# BitHub - Next-Gen Crypto Trading Platform

BitHub is a powerful, user-friendly cryptocurrency trading platform built with Django. It provides a comprehensive suite of features for trading, tracking, and managing cryptocurrency investments with advanced order types and real-time market data.

![BitHub Logo](static/images/favicon-128.png)

## Features

### Trading Features
- **Market Orders**: Buy and sell cryptocurrency instantly at current market prices
- **Limit Orders**: Set orders to execute automatically when prices reach a specific level
- **Stop Orders**: Protect your investments with stop loss or take profit orders
- **Stop-Limit Orders**: Combine stop triggers with limit order precision

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

### Prerequisites
- Python 3.8+
- Redis server
- Git

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/the_bit_hub.git
   cd the_bit_hub
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Populate sample cryptocurrency data**
   ```bash
   python manage.py populate_crypto_data
   ```

8. **Generate static files**
   ```bash
   python manage.py collectstatic
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
