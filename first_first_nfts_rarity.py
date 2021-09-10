"""Compute rarity of First First NFTs.

First First NFTs were created by @_deafbeef.

Author: @ddtg_quant

Reference material
----------
Contract address: https://etherscan.io/address/0xc9cb0fee73f060db66d2693d92d75c825b1afdbf
OpenSea: https://opensea.io/collection/firstproject
"""

# Imports
from collections import Counter, defaultdict
from datetime import datetime
from scipy import stats
from typing import Any, Dict, List, Tuple
from web3 import Web3, exceptions
import matplotlib.pyplot as plt
import numpy as np
import re
import requests
import sys
import time

# Constants
CONTRACT_ADDRESS = '0xc9Cb0FEe73f060Db66D2693D92d75c825B1afdbF'
ETHERSCAN_API_KEY = 'YOUR-ETHERSCAN-API-KEY'
INFURA_PROJECT_ID = 'YOUR-PROJECT-ID'
LIMIT = 50  # 50 NFT limit per query of OpenSea API
MAX_SUPPLY = 5000  # Number of First First NFTs
THOUSAND = 1000
HUNDRED = 100
ROUND_DIGITS = 2
PROGRESS_BAR_LENGTH = (MAX_SUPPLY / THOUSAND)  # 5 slots for progress bar
OPENSEA_API_SLEEP_TIME = .1  # Seconds between queries to avoid rate limiting
INFURA_API_SLEEP_TIME = .002  # Seconds between queries to avoid rate limiting
REGEX = '[^0-9a-zA-Z%-\\.]+'  # Regex to parse out non-alphanumeric characters except '%', '-', and '.'


def send_request(url: str) -> requests.models.Response:
    """Send a request to an endpoint.

    Args:
        url (str): Endpoint.

    Returns:
        response (Response): Request response.
    """

    try:
        response = requests.get(url)
        response.raise_for_status()

        return response
    except requests.exceptions.HTTPError as errh:
        print(f'HTTP Error: {errh}')
    except requests.exceptions.ConnectionError as errc:
        print(f'Connection Error: {errc}')
    except requests.exceptions.Timeout as errt:
        print(f'Timeout Error: {errt}')
    except requests.exceptions.RequestException as err:
        print(f'Something Else: {err}')
    exit()


def connect_to_contract() -> Any:
    """Connect to Ethereum contract using Web3.

    Returns:
        contract (Contract): Ethereum contract.
    """

    w3 = Web3(Web3.HTTPProvider(f'https://mainnet.infura.io/v3/{INFURA_PROJECT_ID}'))
    response = send_request(f'https://api.etherscan.io/api?module=contract&action=getabi&address={CONTRACT_ADDRESS}&apikey={ETHERSCAN_API_KEY}')
    abi = response.json()['result']
    checksum_address = w3.toChecksumAddress(CONTRACT_ADDRESS)
    contract = w3.eth.contract(address=checksum_address, abi=abi)

    return contract


def print_start_time(message: str) -> datetime:
    """Print start time.

    Args:
        message (str): Message to print.

    Returns:
        start (datetime): Start time.
    """

    start = datetime.now()
    print(f'{message} {start}')

    return start


def print_progress_bar(count: int) -> None:
    """Print progress bar in 20% increments.

    Args:
        count (int): Number of 1000 query chunks.
    """

    # left side of progress bar
    progress_bar = '['

    # Fill in progress bar
    for i in range(0, count):
        progress_bar += '#'

    # Fill in remaining slots with an underscore
    while len(progress_bar) <= PROGRESS_BAR_LENGTH:
        progress_bar += '_'

    # Right side of progress bar
    progress_bar += ']'

    print(f'PROGRESS: {progress_bar}')


def get_claimed_token_ids() -> List[int]:
    """Get claimed Token IDs using OpenSea API.

    This step is required because only 5000 Token IDs were minted out of a possible space of (1, 999999).
    https://twitter.com/_deafbeef/status/1434972438803144706

    Returns:
        claimed (list[int]): List of claimed Token IDs.
    """

    # Initialize
    claimed = []
    offset = 0

    while offset <= (MAX_SUPPLY - LIMIT):
        response = send_request(f'https://api.opensea.io/api/v1/assets?offset={offset}&limit={LIMIT}&asset_contract_address={CONTRACT_ADDRESS}')

        for nft in response.json()['assets']:
            claimed.append(int(nft['token_id']))

        offset += LIMIT

        # Print progress every 1000 queries
        if offset == LIMIT or (offset % THOUSAND) == 0:
            print_progress_bar(offset // THOUSAND)

        time.sleep(OPENSEA_API_SLEEP_TIME)

    return claimed


def print_end_time(message: str, start: datetime) -> None:
    """Print end time.

    Args:
        message (str): Message to print.
        start (datetime): Start time.
    """

    end = datetime.now()

    print(f'{message} {end}')
    print(f'DURATION: {end - start}\n')


def organize_text_data(claimed: List[int], contract: Any) -> Tuple[List[str], List[int], List[str], Dict[str, List[int]], Dict[int, List[int]], Dict[str, List[int]]]:
    """Organizes text data.

    Args:
        claimed (list[int]): List of claimed Token IDs.
        contract (Contract): Ethereum contract.

    Returns:
        output_words (list[str]): List of words used in text.
        output_total_word_counts (list[int]): List of count of words used in each text.
        output_complete_texts (list[str]): List of complete texts.
        output_word_to_token_id (dict[str: list[int]]): Word to Token ID mapping.
        output_total_word_count_to_token_id (dict[int: list[int]]): Total word count to Token ID mapping.
        output_complete_text_to_token_id (dict[str, list[int]]): Complete text to Token ID mapping.
    """

    # Initialize
    output_words = []
    output_total_word_counts = []
    output_complete_texts = []
    output_word_to_token_id = defaultdict(lambda: [])
    output_total_word_count_to_token_id = defaultdict(lambda: [])
    output_complete_text_to_token_id = defaultdict(lambda: [])

    for query_progress_count, token_id in enumerate(claimed):
        try:
            # Get text
            text = contract.functions.getString(token_id).call()
            text = text.lower()
            text = text[:len(text) - 1]  # Remove period at end of text
            output_complete_texts.append(text)

            # Populate complete text to Token ID mapping
            output_complete_text_to_token_id[text].append(token_id)

            # Replace non-alphanumeric characters with a space, but keep % and - symbols
            text = re.sub(REGEX, ' ', text)

            # Remove empty strings from list
            text = text.split(' ')
            text = [item for item in text if item != '']

            # Store words and total word counts
            output_words.append(text)
            output_total_word_counts.append(len(text))

            # Populate word to Token ID mapping
            for word in text:
                output_word_to_token_id[word].append(token_id)

            # Populate total word count to Token ID mapping
            output_total_word_count_to_token_id[len(text)].append(token_id)

            # Print progress every 1000 queries
            if query_progress_count == 0 or ((query_progress_count + 1) % THOUSAND) == 0:
                print_progress_bar((query_progress_count + 1) // THOUSAND)

            time.sleep(INFURA_API_SLEEP_TIME)
        except exceptions.SolidityError as error:
            print(error)
            exit()

    # Flatten list of lists
    output_words = [item for sub in output_words for item in sub]

    return output_words, output_total_word_counts, output_complete_texts, output_word_to_token_id, \
        output_total_word_count_to_token_id, output_complete_text_to_token_id


def print_descriptive_stats(word_data: List[int], type_text: str, detail_text: str) -> None:
    """Print descriptive statistics.

    Args:
        word_data (list[int]): List of word lengths or total word counts.
        type_text (str): WORD or TEXT.
        detail_text (str): CHARACTERS or WORDS.
    """

    # Calculate descriptive statistics
    mean = round(float(np.mean(word_data)), ROUND_DIGITS)
    median = round(float(np.median(word_data)), ROUND_DIGITS)
    mode = stats.mode(word_data)[0][0]
    std = round(float(np.std(word_data)), ROUND_DIGITS)

    print(f'{type_text} INFO')
    print(f'MEAN {type_text} LENGTH: {mean} {detail_text}')
    print(f'MEDIAN {type_text} LENGTH: {median} {detail_text}')
    print(f'MODE {type_text} LENGTH: {mode} {detail_text}')
    print(f'STANDARD DEVIATION OF {type_text} LENGTH: {std} {detail_text}')


def print_longest_word(word_data: List[str]) -> None:
    """Print longest word.

    Args:
        word_data (list[str]): All words used in text.
    """

    longest_word = ''

    for word in word_data:
        if len(word) > len(longest_word):
            longest_word = word

    print(f'LONGEST WORD: {longest_word}')


def print_distinct_words(word_data: List[str]) -> None:
    """Print distinct words.

    Args:
        word_data (list[str]): All words used in text.
    """

    word_data_dedup = list(set(word_data))
    num_words = len(word_data_dedup)

    print(f'NUMBER OF DISTINCT WORDS: {num_words}')
    print(f'TOTAL WORDS: {len(word_data)}\n')


def generate_plot(data: List[int], bins: range, type_text: str, detail_text: str) -> None:
    """Generate and save histogram.

    Args:
        data (list[int]): List of word lengths or total word counts.
        bins (range): Bins.
        type_text (str): WORD or TEXT.
        detail_text (str): CHARACTERS or WORDS.
    """

    # Plot histogram
    plt.hist(x=data, bins=bins, density=True, facecolor='lightskyblue', alpha=0.75)

    # Plot settings
    # General
    plt.title(f'Histogram of {type_text} Length')
    plt.grid(True)

    # X-axis
    plt.xlabel(f'{type_text} Length ({detail_text})')
    plt.xlim(0, 30)
    plt.xticks(bins)
    ax = plt.gca()
    plt.setp(ax.get_xticklabels()[1::2], visible=False)

    # Y-axis
    plt.ylabel('Probability')
    plt.ylim(0, .25)

    # Save plot
    filename = f'histogram_of_{type_text}_length.png'
    filename = filename.lower()
    plt.savefig(filename)
    plt.clf()


def get_rarity(data: List[int or str], mapping: Dict[str or int, List[int]], total: int) -> List[Tuple[str or int, int, str, List[int]]]:
    """Get counts and rarity.

    Args:
        data (list[str or int]): Data to count and compute rarity for.
        mapping (dict[str or int, list[int]]): Maps data to Token IDs.
        total (int): Denominator used when computing rarity.

    Returns:
        output (list[tuple[str or int, int, str, list[int]]]): Comma-delimited list of text, count, rarity, and Token ID pairings.
    """

    # Get count
    counter = Counter(data)
    rarity = Counter()

    # Calculate rarity
    for key, value in counter.items():
        rarity[key] = str(round((value / total) * HUNDRED, ROUND_DIGITS)) + '%'

    # Create and sort list of tuples
    output = [(key, value, rarity[key], mapping[key]) for key, value in counter.items()]
    output = sorted(output, key=lambda x: x[1])

    return output


def write_to_file(filename: str, header: str, data: List[Tuple[str or int, int, str, List[int]]]) -> None:
    """Write output to file.

    Args:
        filename (str): Name of file.
        header (str): Comma-delimited list of column names.
        data (list[tuple[str or int, int, str, list[int]]]): Pairings of text, count, rarity, and a list of Token IDs.
    """

    with open(filename, 'w') as f:
        sys.stdout = f

        print(header)
        for text, count, rarity, token_ids in data:
            token_ids = [str(item) for item in token_ids]
            token_ids = ';'.join(token_ids)

            print(f'{text},{count},{rarity},[{token_ids}]')

        sys.stdout.close()


if __name__ == '__main__':
    # Connect to NFT contract
    nft_contract = connect_to_contract()

    # Get claimed Token IDs
    starting_time = print_start_time('STARTED COLLECTING CLAIMED TOKEN IDS:')
    claimed_token_ids = get_claimed_token_ids()
    print_end_time('FINISHED COLLECTING CLAIMED TOKEN IDS:', starting_time)

    # Sanity check
    if len(claimed_token_ids) != MAX_SUPPLY:
        print('There should be 5000 tokens. Something went wrong.')
        exit()

    # Organize data for words, word counts, and complete texts
    starting_time = print_start_time('STARTED QUERYING CONTRACT:')
    words, total_word_counts, complete_texts, word_to_token_id, \
        total_word_count_to_token_id, complete_text_to_token_id = organize_text_data(claimed_token_ids, nft_contract)
    print_end_time('FINISHED QUERYING CONTRACT:', starting_time)

    # Print descriptive statistics for word lengths
    word_lengths = [len(word) for word in words]
    print_descriptive_stats(word_data=word_lengths, type_text='WORD', detail_text='CHARACTERS')

    # Print longest word
    print_longest_word(words)

    # Print number of distinct words
    print_distinct_words(words)

    # Plot word length histogram
    generate_plot(data=word_lengths, bins=range(31), type_text='Word', detail_text='Characters')

    # Print descriptive statistics for text length
    print_descriptive_stats(word_data=total_word_counts, type_text='TEXT', detail_text='WORDS')

    # Plot text length histogram
    generate_plot(data=total_word_counts, bins=range(31), type_text='Text', detail_text='Words')

    # Get counts, rarity, and Token IDs for words, word counts, and complete texts
    words = get_rarity(data=words, mapping=word_to_token_id, total=len(words))
    total_word_counts = get_rarity(data=total_word_counts, mapping=total_word_count_to_token_id, total=MAX_SUPPLY)
    complete_texts = get_rarity(data=complete_texts, mapping=complete_text_to_token_id, total=MAX_SUPPLY)

    # Write results to file
    write_to_file(filename='words.txt', header='WORD,COUNT,RARITY,TOKEN_ID', data=words)
    write_to_file(filename='total_word_counts.txt', header='TOTAL_WORD_COUNT,COUNT,RARITY,TOKEN_ID', data=total_word_counts)
    write_to_file(filename='complete_texts.txt', header='COMPLETE_TEXT,COUNT,RARITY,TOKEN_ID', data=complete_texts)
