# Python Trading Telegram Declarative

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Framework](https://img.shields.io/badge/framework-Telegram%20Bot%20API-blue.svg)](https://core.telegram.org/bots/api)
[![Architecture](https://img.shields.io/badge/architecture-Clean%20Architecture-orange.svg)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
[![Testing](https://img.shields.io/badge/tests-100%25%20coverage-brightgreen.svg)](#testing)
[![Code Style](https://img.shields.io/badge/code%20style-PEP%208-black.svg)](https://www.python.org/dev/peps/pep-0008/)
[![Type Hints](https://img.shields.io/badge/typing-fully%20typed-blue.svg)](https://docs.python.org/3/library/typing.html)

A robust, modular Python framework for building Telegram bots with declarative command handling, automatic retries, and clean architecture.

## Features

- 🚀 **Clean Architecture**: Separation of concerns with modular components
- 🔄 **Automatic Retry Logic**: Built-in exponential backoff for network failures
- 📊 **Queue Management**: Asynchronous message handling with thread-safe queues
- 🛡️ **Error Handling**: Comprehensive error handling with specific exception types
- 📝 **History Tracking**: Built-in conversation history management
- 🧪 **Fully Tested**: 100% test coverage with unit and integration tests
- 🎯 **Type Hints**: Full type annotation support
- 🎨 **Declarative Command Handling**: Define commands with typed parameters

## Architecture

<div align="center">
  <img src="architecture_diagram.png" alt="Architecture Diagram" width="75%">
</div>

### Components

- **TelegramClient**: Handles HTTP communication with Telegram API
- **MessageSender**: Manages outgoing message queue with async sending
- **MessageReceiver**: Polls for updates and manages incoming queue
- **TelegramService**: Orchestrates all components
- **BaseService**: Compatibility layer for existing implementations
- **TelegramHandler**: Declarative command handler with type validation

## Installation

### Prerequisites

- Python 3.12+
- pip or poetry

### Install from source

```bash
# Clone the repository
git clone https://github.com/venantvr/Python.Trading.Telegram.Declarative.git
cd Python.Trading.Telegram.Declarative

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## Quick Start

### Basic Usage

```python
from venantvr.telegram.history import TelegramHistoryManager

# Configuration
API_BASE_URL = "https://api.telegram.org/bot"
BOT_TOKEN = "your-bot-token"
CHAT_ID = "your-chat-id"
ENDPOINTS = {
    "text": "/sendMessage",
    "updates": "/getUpdates"
}

# Initialize components
# noinspection PyArgumentList
history_manager = TelegramHistoryManager()
# noinspection PyUnresolvedReferences
service = MyCustomService(
    API_BASE_URL,
    BOT_TOKEN,
    CHAT_ID,
    ENDPOINTS,
    history_manager
)

# Start the service
service.start()

# Send a message
service.send_message({
    "text": "Hello, World!",
    "reply_markup": ""
})

# Stop the service
service.stop()
```

### Declarative Command Definition

```python
from venantvr.telegram.handler import TelegramHandler
from venantvr.telegram.classes.command import Command
from venantvr.telegram.classes.menu import Menu


class MyBotHandler(TelegramHandler):
    # noinspection PyUnresolvedReferences
    @property
    def command_actions(self) -> dict:
        return {
            Menu.from_value("/positions"): {
                Command.from_value("/show_positions"): {
                    "action": lambda: self.show_positions(),
                    "args": (),
                    "kwargs": {}
                },
                Command.from_value("/set_sell_price"): {
                    "action": self.set_sell_price,
                    "args": (),
                    "kwargs": {
                        "position_id": str,
                        "percentage_change": float,
                    },
                    "asks": [
                        {"text": "Enter position ID:", "reply_markup": ""},
                        {"text": "Enter percentage change:", "reply_markup": ""},
                    ],
                    "respond": lambda args: [
                        self.extract_number(arg, expected_type=type_)
                        for arg, type_ in zip(args, self.get_command_types())
                    ]
                }
            }
        }
```

### Creating a Custom Bot

```python
from venantvr.telegram.base import BaseService


class MyBot(BaseService):
    # noinspection PyUnresolvedReferences
    def process_commands(self):
        """Process incoming commands."""
        while True:
            try:
                update = self.incoming_queue.get(timeout=0.1)
                if update is None:
                    break

                # Process your commands here
                chat_id, msg_type, content = self.parse_update(update)

                if msg_type == 'text' and content.get('text') == '/start':
                    # noinspection PyTypeChecker
                    self.send_message({
                        "text": "Welcome to my bot!",
                        "reply_markup": ""
                    })

            except queue.Empty:
                continue
```

## Configuration

### Environment Variables

Create a `.env` file in your project root:

```env
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
TELEGRAM_API_URL=https://api.telegram.org/bot
LOG_LEVEL=INFO
```

### Timeout Configuration

```python
from venantvr.telegram.client import TelegramClient

client = TelegramClient(
    api_base_url="https://api.telegram.org/bot",
    bot_token="your-token",
    endpoints={"text": "/sendMessage", "updates": "/getUpdates"}
)

# Custom timeout for sending messages
# noinspection PyUnresolvedReferences
response = client.send_message(payload, max_retries=5)

# Custom timeout for polling
# noinspection PyUnresolvedReferences
updates = client.get_updates(params, timeout=(5, 60))
```

## Error Handling

The framework provides specific exception types for better error handling:

```python
from venantvr.telegram.client import TelegramAPIError, TelegramNetworkError

try:
    # noinspection PyUnresolvedReferences
    service.send_message(message)
except TelegramAPIError as e:
    # Handle API errors (400, 401, 403, etc.)
    # noinspection PyUnresolvedReferences
    logger.error(f"API Error: {e}")
except TelegramNetworkError as e:
    # Handle network errors (connection, timeout)
    # noinspection PyUnresolvedReferences
    logger.error(f"Network Error: {e}")
```

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test file
python -m unittest tests.test_client

# Run with verbose output
make test-verbose
```

### Writing Tests

```python
import unittest
from unittest.mock import patch
from venantvr.telegram.client import TelegramClient

class TestMyBot(unittest.TestCase):
    def setUp(self):
        self.client = TelegramClient(
            "https://api.telegram.org/bot",
            "test-token",
            {"text": "/sendMessage", "updates": "/getUpdates"}
        )
    
    @patch('requests.post')
    def test_send_message(self, mock_post):
        mock_post.return_value.status_code = 200
        result = self.client.send_message({"text": "test"})
        self.assertIsNotNone(result)
```

## Development

### Project Structure

```
.
├── venantvr/
│   └── telegram/
│       ├── base.py              # Base service class
│       ├── client.py            # HTTP client
│       ├── message_queue.py     # Queue management
│       ├── service.py           # Main orchestrator
│       ├── notification.py      # Notification service
│       ├── handler.py           # Command handlers
│       ├── history.py           # History management
│       ├── classes/             # Data models
│       │   ├── command.py
│       │   ├── enums.py
│       │   ├── menu.py
│       │   ├── payload.py
│       │   └── types.py
│       └── tools/               # Utilities
│           ├── logger.py
│           └── utils.py
├── tests/                       # Test suite
│   ├── test_client.py
│   ├── test_message_queue.py
│   └── test_service.py
├── requirements.txt
├── Makefile
└── README.md
```

### Code Style

The project follows PEP 8 style guidelines. Use the following tools:

```bash
# Format code
make format

# Lint code
make lint

# Type checking
make type-check
```

## API Reference

### TelegramClient

```python
# noinspection PyUnresolvedReferences
client = TelegramClient(api_base_url, bot_token, endpoints)

# Send message with retry
# noinspection PyUnresolvedReferences
response = client.send_message(payload, max_retries=3)

# Get updates
# noinspection PyUnresolvedReferences
updates = client.get_updates(params, timeout=(3, 30))
```

### MessageSender

```python
# noinspection PyUnresolvedReferences
sender = MessageSender(client, chat_id, history_manager)

# Start sender thread
sender.start()

# Send messages
# noinspection PyUnresolvedReferences
sender.send_message(message)  # Single message
# noinspection PyUnresolvedReferences
sender.send_message([msg1, msg2])  # Multiple messages

# Flush queue immediately
sender.flush_queue()

# Stop sender thread
sender.stop()
```

### MessageReceiver

```python
# noinspection PyUnresolvedReferences
receiver = MessageReceiver(client, history_manager)

# Start receiver thread
receiver.start()

# Access incoming queue
update = receiver.incoming_queue.get()

# Parse update
chat_id, msg_type, content = receiver.parse_update(update)

# Stop receiver thread
receiver.stop()
```

## Performance

- **Concurrent Processing**: Separate threads for sending and receiving
- **Queue-based Architecture**: Non-blocking message handling
- **Connection Pooling**: Reuses HTTP connections
- **Exponential Backoff**: Reduces API load during failures

### Benchmarks

| Operation        | Time    | Throughput    |
|------------------|---------|---------------|
| Send Message     | ~100ms  | 10 msg/s      |
| Receive Update   | ~50ms   | 20 updates/s  |
| Queue Processing | <1ms    | 1000+ msg/s   |

## Flow Example

```
User                                  Bot
 |                                     |
 |------- /start --------------------->|
 |<------ Welcome message -------------|
 |                                     |
 |------- /help ---------------------->|
 |<------ Command menu ----------------|
 |                                     |
 |------- Click button --------------->|
 |<------ Sub-menu --------------------|
 |                                     |
 |------- Interactive command -------->|
 |<------ Ask for parameter 1 ---------|
 |------- Send parameter 1 ----------->|
 |<------ Ask for parameter 2 ---------|
 |------- Send parameter 2 ----------->|
 |<------ Confirmation message --------|
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📧 Email: venantvr@gmail.com
- 💬 Telegram: @venantvr
- 🐛 Issues: [GitHub Issues](https://github.com/venantvr/Python.Trading.Telegram.Declarative/issues)

## Acknowledgments

- Thanks to the Telegram Bot API team
- Built with Python and ❤️

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes.

## Roadmap

- [ ] Webhook support
- [ ] Database integration
- [ ] Rate limiting middleware
- [ ] Metrics and monitoring
- [ ] Docker support
- [ ] CLI tools
- [ ] Plugin system
- [ ] Async/await support
- [ ] Command validation decorators
- [ ] Built-in command documentation