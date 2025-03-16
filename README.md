# the_bit_hub
this is a bitcoin trading application which helps facilitate trades

## Django Application
This project is built using Django, a high-level Python web framework that encourages rapid development and clean, pragmatic design.

## Features

### User Authentication and Authorization
- Secure user authentication and authorization using Django's built-in mechanisms.

### Trade Management
- Create, view, and manage Bitcoin trades.
- Trade model with fields for user, trade type, amount, price, and date.
- Mark trades as successful or failed to track trade performance.

### Trader Rating System
- Each user has a trader profile with a rating based on their trading history.
- Ratings are calculated automatically based on successful trade percentage.
- View top traders ranked by their rating.
- View detailed trader profiles showing trade history and success rates.

### Bitcoin Price Integration
- Fetch current Bitcoin prices using the CoinGecko API.

### Security
- HTTPS for secure communication.
- Security settings to prevent common web vulnerabilities (XSS, CSRF, clickjacking, etc.).

### Templates
- HTML templates for listing trades and creating new trades.
- Profile pages to display trader ratings and trade history.

### Error Handling
- Graceful error handling to avoid exposing sensitive information.

### Deployment
- Ready for deployment to a production server.
