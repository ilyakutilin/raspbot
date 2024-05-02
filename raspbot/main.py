import argparse
import asyncio
import os
import sys

current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))

if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from raspbot.bot.bot import start_bot  # noqa

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Telegram Raspbot")
    parser.add_argument(
        "-t", "--test", action="store_true", help="Run in test environment"
    )
    args = parser.parse_args()

    if args.test:
        asyncio.run(start_bot(test=True))
    else:
        asyncio.run(start_bot())
