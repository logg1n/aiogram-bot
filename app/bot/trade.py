from pybit.unified_trading import HTTP


def get_info_ticker(ticker) -> dict | str:
    session = HTTP(testnet=True)
    response: dict = session.get_tickers(
        category="spot",
        symbol=ticker,
    )

    keys_copy = [
        "symbol",
        "lastPrice",
    ]

    info = {}
    if response["retCode"] == 0:
        result_list = response.get("result", {}).get("list", [])
        if result_list and len(result_list) > 0:
            for key in keys_copy:
                if key in result_list[0]:
                    info[key] = result_list[0][key]
    else:
        "Информации о паре нет!"

    return info
