# BitHub - Next-Gen Crypto Trading Platform

BitHub is a powerful, user-friendly cryptocurrency trading platform built with Django. It provides a comprehensive suite of features for trading, tracking, and managing cryptocurrency investments with advanced order types and real-time market data.

![BitHub Logo](static/images/favicon-128.png)

## Features

### Trading Features
- **Market Orders**: Buy and sell cryptocurrency instantly at current market prices
- **Limit Orders**: Set orders to execute automatically when prices reach a specific level
- **Stop Orders**: Protect your investments with stop loss or take profit orders
- **Stop-Limit Orders**: Combine stop triggers with limit order precision
- **Crypto Conversion**: Easily convert between different cryptocurrencies
- **Tax Reporting**: Generate tax reports for your trading activity

### Platform Features
- **Real-time Price Charts**: View cryptocurrency price movements with interactive charts
- **Portfolio Dashboard**: Track your crypto assets and overall performance
- **Transaction History**: Detailed history of all your trading activity
- **Wallet Management**: Securely manage multiple cryptocurrency wallets
- **Watchlists**: Track your favorite cryptocurrencies in customizable lists
- **Dark Mode**: Comfortable viewing experience with light and dark themes

## Technology Stack

- **Backend**: Django 4.1+
- **Frontend**: Bootstrap 5, JavaScript, Chart.js
- **Database**: SQLite (development), PostgreSQL (recommended for production)
- **Task Scheduling**: Django Q with Redis
- **Styling**: Custom CSS with dynamic theme support

## Installation

### Automated Installation

#### Windows
1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/the_bit_hub.git
   cd the_bit_hub
   ```

2. Run the installer script
   ```bash
   install.bat
   ```

#### Linux/Mac
1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/the_bit_hub.git
   cd the_bit_hub
   ```

2. Make the installer script executable and run it
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

### Manual Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/the_bit_hub.git
   cd the_bit_hub
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv env
   ```

3. **Activate the virtual environment**
   - Windows: `env\Scripts\activate`
   - Linux/Mac: `source env/bin/activate`

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run setup script**
   ```bash
   python setup.py
   ```

## Running the Application

1. **Start the Redis server**
   - Windows: Start Redis service from WSL or Redis Windows port
   - Linux/Mac: `redis-server`

2. **Start the Django Q cluster**
   ```bash
   python manage.py qcluster
   ```

3. **Run the Django development server**
   ```bash
   python manage.py runserver
   ```

4. Access the application at http://127.0.0.1:8000/

## Deployment

For production deployment, consider the following:

1. **Environment Variables**: Set up environment variables for sensitive information
   - SECRET_KEY
   - DATABASE credentials
   - DEBUG mode (should be False)

2. **Database**: Switch to PostgreSQL for production use

3. **Web Server**: Use Gunicorn as the WSGI server and Nginx as the reverse proxy

4. **Static Files**: Configure a static file server or use a CDN

5. **Scheduled Tasks**: Ensure the Django Q cluster is running (consider using Supervisor or systemd)

## Development

### Project Structure
- `trading_hub/` - Main application directory
  - `models.py` - Database models including crypto, orders, transactions
  - `views.py` - View functions for rendering templates and handling requests
  - `templates/` - HTML templates
  - `management/commands/` - Custom Django management commands
  - `templatetags/` - Custom template tags and filters

### Adding New Features
1. Update models in `models.py` if needed
2. Create migrations: `python manage.py makemigrations`
3. Apply migrations: `python manage.py migrate`
4. Add view functions in `views.py`
5. Create templates in `templates/trading_hub/`
6. Update URL patterns in `urls.py`

## Testing

### Test Coverage

BitHub implements comprehensive test coverage for all critical components:

#### Model Testing
- Tests for model creation, validation and methods
- Relationship verification between models
- Business logic tests for financial calculations

#### View Testing
- Authentication requirements
- Response status codes
- Context data verification
- Form submission handling

#### API Testing
- Endpoint availability
- Authentication and permission checks
- Response format validation
- Error handling

#### Integration Testing
- End-to-end transaction workflows
- Order creation and execution
- Wallet balance updates
- Tax calculation accuracy

### Running Tests

Run all tests with coverage report:
```bash
python run_tests.py
```

Run specific test modules:
```bash
python run_tests.py --module models  # Test just models
python run_tests.py --module views   # Test just views
python run_tests.py --module api     # Test just API endpoints
```

Generate HTML coverage report:
```bash
python run_tests.py --html
```

The HTML report will be available in the `htmlcov` directory.

### Test Structure

Tests are organized in the following structure:
- `trading_hub/tests/test_models.py` - Tests for database models
- `trading_hub/tests/test_views.py` - Tests for view functions
- `trading_hub/tests/test_forms.py` - Tests for form validation
- `trading_hub/tests/test_api.py` - Tests for API endpoints
- `trading_hub/tests/test_services.py` - Tests for service functions

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits

- Django - Web framework
- Bootstrap - Frontend framework
- Chart.js - Interactive charts
- Django Q - Task scheduling
- Redis - Message broker for task queue
- Font Awesome - Icons

---

&copy; 2023-2025 BitHub. All rights reserved.
