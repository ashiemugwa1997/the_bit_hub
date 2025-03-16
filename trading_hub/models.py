from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class TraderProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='trader_profile')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    total_trades = models.PositiveIntegerField(default=0)
    successful_trades = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.username}'s Profile (Rating: {self.rating})"

    def calculate_rating(self):
        if self.total_trades > 0:
            success_rate = self.successful_trades / self.total_trades
            # Rating formula: 50% based on success rate (0-5 points) + base rating of 5
            new_rating = (success_rate * 5) + 5
            # Cap rating between 0-10
            self.rating = min(max(new_rating / 2, 0), 5)
            self.save()


# Create trader profile when a user is created
@receiver(post_save, sender=User)
def create_trader_profile(sender, instance, created, **kwargs):
    if created:
        TraderProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_trader_profile(sender, instance, **kwargs):
    if hasattr(instance, 'trader_profile'):
        instance.trader_profile.save()


class Trade(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trades')
    trade_type = models.CharField(max_length=10, choices=[('buy', 'Buy'), ('sell', 'Sell')])
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    is_successful = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.trade_type} - {self.amount} BTC at {self.price} USD"

    def complete_trade(self, successful=True):
        """Mark a trade as complete and update trader rating"""
        self.is_successful = successful
        self.save()

        # Update trader profile
        profile = self.user.trader_profile
        profile.total_trades += 1
        if successful:
            profile.successful_trades += 1
        profile.calculate_rating()
