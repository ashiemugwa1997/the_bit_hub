import os
import csv
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Sum, Q, F

from trading_hub.models import Transaction, TaxReport, TaxTransaction, CryptoCurrency


class TaxCalculator:
    """Service class for cryptocurrency tax calculations"""
    
    COST_BASIS_METHODS = {
        'fifo': 'First In, First Out',
        'lifo': 'Last In, First Out',
        'hifo': 'Highest In, First Out',
        'acb': 'Average Cost Basis'
    }

    def __init__(self, user, tax_year=None, cost_basis_method='fifo'):
        """
        Initialize tax calculator for a user
        
        Args:
            user (User): User to calculate taxes for
            tax_year (int): Tax year to calculate for (defaults to current year)
            cost_basis_method (str): Method for calculating cost basis ('fifo', 'lifo', 'hifo', 'acb')
        """
        self.user = user
        self.tax_year = tax_year or timezone.now().year
        self.cost_basis_method = cost_basis_method
        
        # Date range for tax year
        self.year_start = datetime(self.tax_year, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        self.year_end = datetime(self.tax_year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    def calculate_cost_basis(self, crypto_code):
        """
        Calculate cost basis for a specific cryptocurrency
        
        Args:
            crypto_code (str): Cryptocurrency code (e.g., BTC, ETH)
            
        Returns:
            dict: Dictionary with buy and sell transactions and their cost basis
        """
        # Get all buy transactions (to establish cost basis)
        buys = Transaction.objects.filter(
            user=self.user,
            transaction_type='buy',
            currency=crypto_code,
            status='completed'
        ).order_by('created_at')
        
        # Get sell transactions for the tax year
        sells = Transaction.objects.filter(
            user=self.user,
            transaction_type='sell',
            currency=crypto_code,
            status='completed',
            created_at__gte=self.year_start,
            created_at__lte=self.year_end
        ).order_by('created_at')
        
        # Calculate cost basis based on the selected method
        if self.cost_basis_method == 'fifo':
            return self._fifo_cost_basis(buys, sells)
        elif self.cost_basis_method == 'lifo':
            return self._lifo_cost_basis(buys, sells)
        elif self.cost_basis_method == 'hifo':
            return self._hifo_cost_basis(buys, sells)
        elif self.cost_basis_method == 'acb':
            return self._average_cost_basis(buys, sells)
        else:
            raise ValueError(f"Invalid cost basis method: {self.cost_basis_method}")

    def _fifo_cost_basis(self, buys, sells):
        """
        Calculate cost basis using First In, First Out method
        
        Args:
            buys (QuerySet): Buy transactions
            sells (QuerySet): Sell transactions
            
        Returns:
            dict: Dictionary with cost basis information for each sell transaction
        """
        remaining_buys = []
        for buy in buys:
            remaining_buys.append({
                'transaction': buy,
                'remaining': buy.amount,
                'price_per_unit': buy.native_amount / buy.amount if buy.amount else Decimal('0')
            })
            
        result = []
        for sell in sells:
            sell_amount = sell.amount
            sell_proceeds = sell.native_amount
            cost_basis = Decimal('0')
            matched_amount = Decimal('0')
            is_long_term = True
            
            # Match sell with available buy transactions (FIFO order)
            while sell_amount > 0 and remaining_buys:
                buy = remaining_buys[0]
                
                if buy['remaining'] <= 0:
                    remaining_buys.pop(0)
                    continue
                
                # Check if this is a long-term or short-term gain/loss
                holding_period = sell.created_at - buy['transaction'].created_at
                is_this_match_long_term = holding_period.days >= 365
                
                # If any part of the sell is short-term, the whole sell is short-term
                if not is_this_match_long_term:
                    is_long_term = False
                
                # Determine how much of this buy to use
                use_amount = min(sell_amount, buy['remaining'])
                matched_amount += use_amount
                
                # Calculate cost basis for this portion
                portion_cost = use_amount * buy['price_per_unit']
                cost_basis += portion_cost
                
                # Update the remaining buy amount
                buy['remaining'] -= use_amount
                if buy['remaining'] <= 0:
                    remaining_buys.pop(0)
                    
                # Update the remaining sell amount
                sell_amount -= use_amount
                
            # Calculate gains/losses
            gain_loss = sell_proceeds - cost_basis
            
            # Save this information
            result.append({
                'transaction': sell,
                'cost_basis': cost_basis,
                'proceeds': sell_proceeds,
                'gain_loss': gain_loss,
                'is_long_term': is_long_term,
                'matched_amount': matched_amount
            })
            
        return result

    def _lifo_cost_basis(self, buys, sells):
        """Calculate cost basis using Last In, First Out method"""
        remaining_buys = []
        for buy in buys.order_by('-created_at'):  # Note the reverse order
            remaining_buys.append({
                'transaction': buy,
                'remaining': buy.amount,
                'price_per_unit': buy.native_amount / buy.amount if buy.amount else Decimal('0')
            })
            
        result = []
        for sell in sells:
            sell_amount = sell.amount
            sell_proceeds = sell.native_amount
            cost_basis = Decimal('0')
            matched_amount = Decimal('0')
            is_long_term = True
            
            # Match sell with available buy transactions (LIFO order)
            while sell_amount > 0 and remaining_buys:
                buy = remaining_buys[0]
                
                if buy['remaining'] <= 0:
                    remaining_buys.pop(0)
                    continue
                
                # Check if long-term
                holding_period = sell.created_at - buy['transaction'].created_at
                is_this_match_long_term = holding_period.days >= 365
                
                if not is_this_match_long_term:
                    is_long_term = False
                
                # Determine how much of this buy to use
                use_amount = min(sell_amount, buy['remaining'])
                matched_amount += use_amount
                
                # Calculate cost basis for this portion
                portion_cost = use_amount * buy['price_per_unit']
                cost_basis += portion_cost
                
                # Update the remaining amounts
                buy['remaining'] -= use_amount
                if buy['remaining'] <= 0:
                    remaining_buys.pop(0)
                    
                sell_amount -= use_amount
                
            # Calculate gains/losses
            gain_loss = sell_proceeds - cost_basis
            
            result.append({
                'transaction': sell,
                'cost_basis': cost_basis,
                'proceeds': sell_proceeds,
                'gain_loss': gain_loss,
                'is_long_term': is_long_term,
                'matched_amount': matched_amount
            })
            
        return result

    def _hifo_cost_basis(self, buys, sells):
        """Calculate cost basis using Highest In, First Out method"""
        # Convert buys to list for sorting
        all_buys = []
        for buy in buys:
            price_per_unit = buy.native_amount / buy.amount if buy.amount else Decimal('0')
            all_buys.append({
                'transaction': buy,
                'remaining': buy.amount,
                'price_per_unit': price_per_unit,
                'created_at': buy.created_at
            })
            
        # Sort buys by price (highest first), then by date (oldest first for ties)
        remaining_buys = sorted(all_buys, key=lambda x: (-x['price_per_unit'], x['created_at']))
        
        result = []
        for sell in sells:
            sell_amount = sell.amount
            sell_proceeds = sell.native_amount
            cost_basis = Decimal('0')
            matched_amount = Decimal('0')
            is_long_term = True
            
            # Match sell with available buy transactions (HIFO order)
            while sell_amount > 0 and remaining_buys:
                # Re-sort remaining buys each time to ensure highest price first
                remaining_buys.sort(key=lambda x: (-x['price_per_unit'], x['created_at']))
                buy = remaining_buys[0]
                
                if buy['remaining'] <= 0:
                    remaining_buys.pop(0)
                    continue
                
                # Check if long-term
                holding_period = sell.created_at - buy['transaction'].created_at
                is_this_match_long_term = holding_period.days >= 365
                
                if not is_this_match_long_term:
                    is_long_term = False
                
                # Determine how much of this buy to use
                use_amount = min(sell_amount, buy['remaining'])
                matched_amount += use_amount
                
                # Calculate cost basis for this portion
                portion_cost = use_amount * buy['price_per_unit']
                cost_basis += portion_cost
                
                # Update the remaining amounts
                buy['remaining'] -= use_amount
                if buy['remaining'] <= 0:
                    remaining_buys.remove(buy)
                    
                sell_amount -= use_amount
                
            # Calculate gains/losses
            gain_loss = sell_proceeds - cost_basis
            
            result.append({
                'transaction': sell,
                'cost_basis': cost_basis,
                'proceeds': sell_proceeds,
                'gain_loss': gain_loss,
                'is_long_term': is_long_term,
                'matched_amount': matched_amount
            })
            
        return result

    def _average_cost_basis(self, buys, sells):
        """Calculate cost basis using Average Cost Basis method"""
        # Calculate total bought and cost before each sell
        result = []
        
        for sell in sells:
            # Consider only buys before this sell
            prior_buys = buys.filter(created_at__lt=sell.created_at)
            
            total_amount = prior_buys.aggregate(total=Sum('amount'))['total'] or Decimal('0')
            total_cost = prior_buys.aggregate(total=Sum('native_amount'))['total'] or Decimal('0')
            
            if total_amount > 0:
                avg_cost_per_unit = total_cost / total_amount
                cost_basis = sell.amount * avg_cost_per_unit
                gain_loss = sell.native_amount - cost_basis
                
                # For ACB, we need to determine if the sale is long-term
                # Simplification: check if the average purchase date is more than a year ago
                weighted_dates = [
                    (buy.amount / total_amount) * (sell.created_at - buy.created_at).days 
                    for buy in prior_buys
                ]
                avg_holding_period = sum(weighted_dates) if weighted_dates else 0
                is_long_term = avg_holding_period >= 365
                
                result.append({
                    'transaction': sell,
                    'cost_basis': cost_basis,
                    'proceeds': sell.native_amount,
                    'gain_loss': gain_loss,
                    'is_long_term': is_long_term,
                    'matched_amount': sell.amount
                })
            else:
                # No prior buys, this might be a coin received from elsewhere
                result.append({
                    'transaction': sell,
                    'cost_basis': Decimal('0'),
                    'proceeds': sell.native_amount,
                    'gain_loss': sell.native_amount,  # All proceeds are gains
                    'is_long_term': False,  # Assume short-term
                    'matched_amount': sell.amount
                })
            
        return result

    def generate_tax_report(self, report_format='csv', include_unrealized=False):
        """
        Generate a tax report for the specified year
        
        Args:
            report_format (str): Format of the report ('csv', 'pdf', etc.)
            include_unrealized (bool): Whether to include unrealized gains
            
        Returns:
            TaxReport: The generated tax report object
        """
        # Create a tax report record
        tax_report = TaxReport.objects.create(
            user=self.user,
            tax_year=self.tax_year,
            report_format=report_format,
            include_unrealized_gains=include_unrealized
        )
        
        # Get unique cryptocurrencies the user has transacted with
        crypto_codes = Transaction.objects.filter(
            user=self.user
        ).values_list('currency', flat=True).distinct()
        
        all_transactions = []
        
        # Calculate cost basis for each cryptocurrency
        for crypto_code in crypto_codes:
            transactions = self.calculate_cost_basis(crypto_code)
            all_transactions.extend(transactions)
            
            # Save tax transaction data
            for tx_data in transactions:
                tx = tx_data['transaction']
                TaxTransaction.objects.update_or_create(
                    transaction=tx,
                    defaults={
                        'cost_basis': tx_data['cost_basis'],
                        'gain_loss': tx_data['gain_loss'],
                        'is_long_term': tx_data['is_long_term'],
                        'tax_year': self.tax_year,
                        'tax_category': 'capital_gain'  # Default category
                    }
                )
        
        # If requested, include unrealized gains
        if include_unrealized:
            unrealized_gains = self.calculate_unrealized_gains()
            # We could add these to the report data if needed
        
        # Generate the report file
        file_path = self._create_report_file(all_transactions, tax_report)
        
        # Update the tax report record
        tax_report.report_file = file_path
        tax_report.status = 'completed'
        tax_report.completed_at = timezone.now()
        tax_report.save()
        
        return tax_report

    def _create_report_file(self, transactions, tax_report):
        """
        Create a report file based on the specified format
        
        Args:
            transactions (list): List of transaction data
            tax_report (TaxReport): The tax report object
            
        Returns:
            str: Path to the generated file
        """
        if tax_report.report_format == 'csv':
            return self._create_csv_report(transactions, tax_report)
        elif tax_report.report_format == 'pdf':
            return self._create_pdf_report(transactions, tax_report)
        elif tax_report.report_format in ['turbotax', 'cointracker']:
            return self._create_turbotax_report(transactions, tax_report)
        else:
            raise ValueError(f"Unsupported report format: {tax_report.report_format}")

    def _create_csv_report(self, transactions, tax_report):
        """Create a CSV tax report"""
        report_dir = os.path.join(settings.MEDIA_ROOT, 'tax_reports')
        os.makedirs(report_dir, exist_ok=True)
        
        filename = f"{self.user.username}_tax_report_{self.tax_year}_{tax_report.id}.csv"
        filepath = os.path.join(report_dir, filename)
        
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = [
                'Date', 'Type', 'Asset', 'Amount', 'Proceeds (USD)', 
                'Cost Basis (USD)', 'Gain/Loss (USD)', 'Holding Period'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            # Write transaction data
            for tx_data in transactions:
                tx = tx_data['transaction']
                writer.writerow({
                    'Date': tx.created_at.strftime('%Y-%m-%d'),
                    'Type': tx.transaction_type.capitalize(),
                    'Asset': tx.currency,
                    'Amount': float(tx.amount),
                    'Proceeds (USD)': float(tx_data['proceeds']),
                    'Cost Basis (USD)': float(tx_data['cost_basis']),
                    'Gain/Loss (USD)': float(tx_data['gain_loss']),
                    'Holding Period': 'Long-Term' if tx_data['is_long_term'] else 'Short-Term'
                })
        
        # Return relative path for storage in model
        return os.path.join('tax_reports', filename)

    def _create_pdf_report(self, transactions, tax_report):
        """Create a PDF tax report"""
        report_dir = os.path.join(settings.MEDIA_ROOT, 'tax_reports')
        os.makedirs(report_dir, exist_ok=True)
        
        filename = f"{self.user.username}_tax_report_{self.tax_year}_{tax_report.id}.pdf"
        filepath = os.path.join(report_dir, filename)
        
        # Placeholder - in a real app, generate PDF here using a library like ReportLab
        with open(filepath, 'w') as f:
            f.write(f"PDF Tax Report for {self.user.username}, {self.tax_year}\n")
            f.write("Generated on " + timezone.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
            f.write("This is a placeholder. In a real app, this would be a properly formatted PDF.\n")
            
            # Add summary data
            total_proceeds = sum(tx['proceeds'] for tx in transactions)
            total_cost = sum(tx['cost_basis'] for tx in transactions)
            total_gain = sum(tx['gain_loss'] for tx in transactions)
            
            f.write(f"Total Proceeds: ${total_proceeds}\n")
            f.write(f"Total Cost Basis: ${total_cost}\n") 
            f.write(f"Total Gain/Loss: ${total_gain}\n")
        
        return os.path.join('tax_reports', filename)

    def _create_turbotax_report(self, transactions, tax_report):
        """Create a TurboTax compatible tax report"""
        report_dir = os.path.join(settings.MEDIA_ROOT, 'tax_reports')
        os.makedirs(report_dir, exist_ok=True)
        
        filename = f"{self.user.username}_turbotax_{self.tax_year}_{tax_report.id}.csv"
        filepath = os.path.join(report_dir, filename)
        
        # TurboTax format specification
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = [
                'Date Sold', 'Asset Name', 'Sale Amount', 'Cost Basis', 
                'Date Acquired', 'Gross Proceeds', 'Gain/Loss'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for tx_data in transactions:
                tx = tx_data['transaction']
                # For simplicity, using a placeholder acquisition date
                acquisition_date = (tx.created_at - timedelta(days=400 if tx_data['is_long_term'] else 100)).strftime('%m/%d/%Y')
                
                writer.writerow({
                    'Date Sold': tx.created_at.strftime('%m/%d/%Y'),
                    'Asset Name': tx.currency,
                    'Sale Amount': float(tx.amount),
                    'Cost Basis': float(tx_data['cost_basis']),
                    'Date Acquired': acquisition_date,
                    'Gross Proceeds': float(tx_data['proceeds']),
                    'Gain/Loss': float(tx_data['gain_loss'])
                })
        
        return os.path.join('tax_reports', filename)

    def calculate_unrealized_gains(self):
        """
        Calculate unrealized gains for current holdings
        
        Returns:
            dict: Dictionary of unrealized gains by cryptocurrency
        """
        results = {}
        
        # Get user's wallets
        wallets = self.user.wallets.all()
        
        for wallet in wallets:
            if wallet.currency_code == 'USD' or wallet.balance <= 0:
                continue
                
            try:
                crypto = CryptoCurrency.objects.get(code=wallet.currency_code)
            except CryptoCurrency.DoesNotExist:
                continue
                
            # Current market value
            current_value = wallet.balance * crypto.current_price_usd
            
            # Calculate cost basis using the chosen method
            buys = Transaction.objects.filter(
                user=self.user,
                transaction_type='buy',
                currency=wallet.currency_code,
                status='completed'
            ).order_by('created_at')
            
            # Account for all sells to determine remaining cost basis
            sells = Transaction.objects.filter(
                user=self.user,
                transaction_type='sell',
                currency=wallet.currency_code,
                status='completed'
            )
            total_bought = buys.aggregate(total=Sum('amount'))['total'] or Decimal('0')
            total_sold = sells.aggregate(total=Sum('amount'))['total'] or Decimal('0')
            total_cost = buys.aggregate(total=Sum('native_amount'))['total'] or Decimal('0')
            
            if total_bought > total_sold and total_bought > 0:
                # Calculate adjusted cost basis for remaining coins
                avg_cost_per_unit = total_cost / total_bought
                cost_basis = wallet.balance * avg_cost_per_unit
                unrealized_gain = current_value - cost_basis
                
                results[wallet.currency_code] = {
                    'current_value': current_value,
                    'cost_basis': cost_basis,
                    'unrealized_gain': unrealized_gain,
                    'balance': wallet.balance,
                    'price_per_unit': crypto.current_price_usd
                }
        
        return results

    def get_annual_summary(self):
        """
        Get summary of gains/losses for the tax year
        
        Returns:
            dict: Summary information about gains and losses
        """
        # Query all tax transactions for this user and tax year
        tax_txs = TaxTransaction.objects.filter(
            transaction__user=self.user,
            tax_year=self.tax_year
        )
        
        # Calculate totals
        short_term_gains = tax_txs.filter(is_long_term=False).aggregate(
            total=Sum('gain_loss')
        )['total'] or Decimal('0')
        
        long_term_gains = tax_txs.filter(is_long_term=True).aggregate(
            total=Sum('gain_loss')
        )['total'] or Decimal('0')
        
        # Count transactions
        total_transactions = tax_txs.count()
        
        # Get unrealized gains
        unrealized_gains = self.calculate_unrealized_gains()
        total_unrealized = sum(data['unrealized_gain'] for data in unrealized_gains.values())
        
        return {
            'tax_year': self.tax_year,
            'short_term_gains': short_term_gains,
            'long_term_gains': long_term_gains,
            'total_gains': short_term_gains + long_term_gains,
            'total_transactions': total_transactions,
            'unrealized_gains': total_unrealized,
            'unrealized_details': unrealized_gains
        }
