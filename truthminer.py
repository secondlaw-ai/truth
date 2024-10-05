import asyncio
import json
import os
import time
import websockets
from web3 import Web3
from dotenv import load_dotenv
from functools import cache
from web3.logs import DISCARD

load_dotenv()
from pathlib import Path

# Polygon OptimisticOracleV2Interface
CONTRACT_ADDRESS = "0xeE3Afe347D5C74317041E2618C49534dAf887c24"
# Sample transaction
# https://polygonscan.com/tx/0x343067db86da543f4ac193def7ad2ce23d91671ba3a44f85e70b16d01359cdd2#eventlog
# logs = get_logs(
#     "0x343067db86da543f4ac193def7ad2ce23d91671ba3a44f85e70b16d01359cdd2"
#   )


def w3_client(chain: str = "eth"):
    if chain == "matic":
        w3 = Web3(Web3.HTTPProvider(os.environ["POLYGON_RPC_URI"]))
    elif chain == "eth":
        w3 = Web3(Web3.HTTPProvider(os.environ["ETH_RPC_URI"]))
    # Verify connection
    if not w3.is_connected():
        print("Failed to connect to Polygon network")
        return
    return w3


w3 = w3_client("matic")


def get_contract(address: str):
    abi = json.loads(Path(f"./abi/{address}.json").read_text())
    return w3.eth.contract(address=address, abi=abi)


def get_events_from_block(block: int):
    contract = get_contract(CONTRACT_ADDRESS)
    event_filter = contract.events.ProposePrice.create_filter(from_block=62641375)
    return event_filter.get_all_entries()


def get_new_questions(block: int):
    contract = get_contract(CONTRACT_ADDRESS)
    return contract.events.RequestPrice.create_filter(
        from_block=block,
    ).get_all_entries()


def get_disputes(block: int):
    contract = get_contract(CONTRACT_ADDRESS)
    return contract.events.DisputePrice.create_filter(
        from_block=block,
    ).get_all_entries()


def get_logs(tx_hash: str):
    """get all relevant logs for a hash"""
    events = [
        "RequestPrice",  # first this is posted
        "ProposePrice",  # then someone else posts this (YES or NO)
        "DisputePrice",  # if this called then the contract calls requestVote
        "Settle",  # this is called when this question is Settled (payouts are made)
    ]
    contract = get_contract(CONTRACT_ADDRESS)
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    logs = []
    for event in events:
        logs_ = getattr(contract.events, event)().process_receipt(
            receipt, errors=DISCARD
        )
        logs.append(logs_)
    return dict(zip(events, logs))


def handle_event(event):
    """Get verification events here..."""
    print("Distilling truth for ...", event)
    time.sleep(1)
    print("Distillation completed!")


async def log_loop(event_filter, poll_interval):
    while True:
        for event in event_filter.get_new_entries():
            handle_event(event)
        await asyncio.sleep(poll_interval)


def sync_log_loop(event_filter, poll_interval):
    while True:
        for event in event_filter.get_new_entries():
            handle_event(event)
        time.sleep(poll_interval)


def sync_poll():
    contract = get_contract(CONTRACT_ADDRESS)
    request_price_filter = contract.events.RequestPrice.create_filter(
        from_block="latest",
    )
    log_loop(request_price_filter, 2)


async def async_poll():
    contract = get_contract(CONTRACT_ADDRESS)
    request_price_filter = contract.events.RequestPrice.create_filter(
        from_block="latest",
    )
    return await asyncio.gather(
        (log_loop(request_price_filter, 2)),
    )


if __name__ == "__main__":
    sync_poll()
