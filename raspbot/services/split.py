from raspbot.core.logging import configure_logging, log

logger = configure_logging(__name__)


@log(logger)
def split_string_list(string_list: list[str], limit: int) -> list[list[str]]:
    """Split a list of strings into several lists each not exceeding the symbols limit.

    Args:
        string_list (list[str]): A list of strings that needs splitting.
        limit (int): A limit that each sub-list shall not exceed.

    Returns:
        list[list[str]]: A list of sub-lists split as per the limit.
    """
    # Initialize an empty list to store the split lists
    split_lists = []

    # Initialize variables to keep track of the cumulative symbols count and the
    # current sublist
    symbols_count = 0
    current_list: list[str] = []

    # Iterate over the string list
    for string in string_list:
        # Check if adding the current string will exceed the limit
        if symbols_count + len(string) > limit:
            # Add the current sublist to the split lists
            split_lists.append(current_list)

            # Reset the variables for the new sublist
            symbols_count = 0
            current_list = []

        # Add the current string to the current sublist
        current_list.append(string)

        # Update the cumulative symbols count
        symbols_count += len(string)

    # Add the last sublist to the split lists
    split_lists.append(current_list)

    # Return the list of lists of strings
    return split_lists
