# XRPL DEX API

Token swap API server powered by the XRPL built-in DEX. Built with FastAPI and xrpl-py.

## Features

- **Order Book**: Check bid/ask prices on XRPL DEX
- **Token Swap**: Exchange tokens like XRP, USD
- **Swap Quotes**: Get estimated amounts before swapping (fee included)
- **API Authentication**: X-API-Key based authentication
- **Usage Limits**: Monthly 100 requests per API key

## Tech Stack

- **FastAPI**: Web framework
- **xrpl-py**: XRPL library
- **aiosqlite**: Async SQLite database
- **Uvicorn**: ASGI server
- **WebSocket**: XRPL testnet connection

## Getting Started

### 1. Prerequisites

- Python 3.8+
- pip

### 2. Installation

```bash
# Clone repository
git clone <repository-url>
cd XRPL_DEX/XRPL_DEX

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables

Copy `.env.example` to create `.env` file with your settings.

```bash
cp .env.example .env
```

Configure your `.env` file:

```env
# XRPL Testnet Node
XRPL_NODE=wss://s.altnet.rippletest.net:51233

# Sender Address (testnet address)
SENDER_ADDRESS=rYourAddressHere

# Secret Key (testnet secret)
SENDER_SECRET=sYourSecretHere

# Fee Account (fee receiver)
FEE_ACCOUNT=rFeeAccountHere

# DEX Fee Rate (0.3%)
DEX_FEE_RATE=0.003

# API Server Settings
HOST=0.0.0.0
PORT=8000

# Database (usage limit tracking)
DB_PATH=./usage.db

# API Authentication Keys (comma separated)
API_KEYS=test-api-key-1,demo-key-2
```

### 4. Generate XRPL Testnet Address

Get testnet address and secret key from [XRPL Faucet](https://xrpl.org/xrp-testnet-faucet.html).

### 5. Start Server

```bash
# Development mode (auto-reload)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or
python app/main.py
```

Server starts at `http://localhost:8000`.

## API Usage

### Basic Configuration

All requests must include API key in header:

```
X-API-Key: your-api-key
```

### API Endpoints

#### 1. Order Book

Check bid/ask prices on XRPL DEX.

```http
GET /dex/orderbook?base=XRP&quote=USD&limit=20
```

**Parameters:**
- `base`: Base currency (e.g., XRP, USD)
- `quote`: Quote currency (e.g., XRP, USD)
- `limit: Number of order book entries (default: 20, max: 100)

**Response Example:**
```json
{
  "base": "XRP",
  "quote": "USD",
  "bids": [
    {
      "price": "1.0025",
      "amount": "1000",
      "account": "rAddress1",
      "sequence": 123
    }
  ],
  "asks": [
    {
      "price": "1.0030",
      "amount": "500",
      "account": "rAddress2",
      "sequence": 456
    }
  ],
  "timestamp": "2026-04-30T12:00:00"
}
```

**curl Example:**
```bash
curl -X GET "http://localhost:8000/dex/orderbook?base=XRP&quote=USD&limit=5" \
  -H "X-API-Key: test-api-key-1"
```

#### 2. Swap Quote

Get estimated amounts before actual swap.

```http
GET /dex/quote?from_currency=XRP&to_currency=USD&amount=100
```

**Parameters:**
- `from_currency`: Source currency
- `to_currency`: Destination currency
- `amount: Amount to query

**Response Example:**
```json
{
  "from_currency": "XRP",
  "to_currency": "USD",
  "from_amount": "100",
  "to_amount": "99.700000",
  "fee": "0.300000",
  "fee_rate": "0.003",
  "estimated_amount": "99.400000",
  "timestamp": "2026-04-30T12:00:00"
}
```

**curl Example:**
```bash
curl -X GET "http://localhost:8000/dex/quote?from_currency=XRP&to_currency=USD&amount=100" \
  -H "X-API-Key: test-api-key-1"
```

#### 3. Token Swap

Execute token swap on XRPL DEX. (Currently in demo mode)

```http
POST /dex/swap
Content-Type: application/json
X-API-Key: your-api-key

{
  "from_currency": "XRP",
  "to_currency": "USD",
  "amount": "100"
}
```

**Request Body:**
- `from_currency`: Source currency
- `to_currency`: Destination currency
- `amount: Swap amount

**Response Example:**
```json
{
  "success": true,
  "tx_hash": "7CD187CA91D394B4A42EC14FB5B0BC7FA3D0AD21BF8B3A316ABCE8050799A5EA",
  "from_currency": "XRP",
  "to_currency": "USD",
  "from_amount": "100",
  "to_amount": "99.700000",
  "fee": "0.300000",
  "fee_rate": "0.003",
  "error": null,
  "timestamp": "2026-04-30T12:00:00"
}
```

**curl Example:**
```bash
curl -X POST "http://localhost:8000/dex/swap" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-api-key-1" \
  -d '{
    "from_currency": "XRP",
    "to_currency": "USD", 
    "amount": "50"
  }'
```

#### 4. Supported Tokens

Get list of supported tokens.

```http
GET /dex/tokens
```

**Response Example:**
```json
{
  "tokens": [
    {
      "currency": "XRP",
      "issuer": null,
      "name": "XRP",
      "decimals": 6
    },
    {
      "currency": "USD",
      "issuer": "rvYAfWj5gh67QVQisdnQzVQZ75Y2uTxgg",
      "name": "USD (Bitstamp)",
      "decimals": 6
    }
  ],
  "count": 2,
  "timestamp": "2026-04-30T12:00:00"
}
```

**curl Example:**
```bash
curl -X GET "http://localhost:8000/dex/tokens"
```

#### 5. Usage Statistics

Get current API key usage statistics.

```http
GET /dex/usage
X-API-Key: your-api-key
```

**Response Example:**
```json
{
  "this_month": 45,
  "last_month": 120,
  "total": 165,
  "monthly_limit": 100,
  "remaining": 55
}
```

## Fee Structure

- **Fee Rate**: 0.3% (DEX_FEE_RATE)
- Fee is automatically deducted from swap amount
- Fee is sent to FEE_ACCOUNT (to be implemented)

## Supported Tokens

Currently supporting the following tokens on **testnet**:

- **XRP**: Native token
- **USD**: Bitstamp USD (rvYAfWj5gh67QVQisdnQzVQZ75Y2uTxgg)

## Development Environment

### Project Structure

```
XRPL_DEX/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── models.py         # Pydantic data models
│   ├── dex_client.py     # XRPL DEX client
│   ├── auth.py           # API authentication middleware
│   └── *.py              # Other helpers
├── requirements.txt
├── .env.example
├── .env                  # Environment variables (not in git)
└── README_EN.md
```

### API Documentation

After server starts, API documentation available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Security Best Practices

1. **API Key Security**: Never include API keys in code or expose publicly
2. **HTTPS**: Use HTTPS in production
3. **Environment Variables**: Add `.env` to `.gitignore`
4. **CORS Configuration**: Restrict to specific origins in production
5. **Usage Monitoring**: Regularly check usage and adjust limits

## Roadmap

### Phase 1: Mainnet Deployment
- Deploy to mainnet (change environment variables)
- Implement real transaction submission
- Add transaction status tracking

### Phase 2: RLUSD Integration
- **RLUSD (Liberty USD)** Support
- Add other stablecoins (USDC, etc.)
- Multi-collateral swaps

### Phase 3: Real Swap Implementation
- Currently in **demo mode** (`demo_tx_*` hash)
- Real OfferCreate transaction submission
- Transaction status tracking
- Auto-retry logic

### Phase 4: Advanced Features
- Limit Order support
- Partial fill swaps
- Slippage protection
- Gas optimization

## Current Limitations

- **Testnet Only**: Currently running on XRPL testnet
- **Testnet Liquidity Issues**: Swaps may not fill due to insufficient order book liquidity
- **Fee Processing**: Currently fee deduction only, actual transfer pending
- **Order Book**: May be empty due to testnet characteristics

## MCP Server Usage

Run the XRPL DEX API as an MCP (Model Context Protocol) server to integrate with other applications.

### Installation

```bash
pip install -r requirements.txt
```

### Run MCP Server

```bash
# DEX API server (required)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# MCP server (another terminal)
python mcp_server.py
```

### Testing

```bash
# Test MCP server
python test_mcp_server.py
```

### Available MCP Tools

1. **get_orderbook**: Get order book
   - Parameters: base, quote, limit
   - Calls DEX API `/dex/orderbook`

2. **get_quote**: Get swap quote
   - Parameters: from_currency, to_currency, amount
   - Calls DEX API `/dex/quote`

3. **swap_tokens**: Execute token swap
   - Parameters: from_currency, to_currency, amount
   - Calls DEX API `/dex/swap`

4. **get_tokens**: Get supported tokens list
   - Parameters: none
   - Calls DEX API `/dex/tokens`

### Environment Variables

Add MCP settings to your `.env` file:

```env
MCP_API_KEY=your-mcp-api-key
MCP_API_BASE_URL=http://localhost:8000
```

### Communication Method

- JSON-RPC 2.0 protocol
- stdio (standard input/output) based communication
- Compatible with other MCP clients

## License

MIT License

## Support

For issues, create an Issue or contact repository maintainers.

---

**Practice safe trading in the slippage & swap at your own risk!**
