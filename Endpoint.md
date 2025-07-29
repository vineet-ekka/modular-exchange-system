### Kraken Endpoints

| | Response Body Tag | Endpoint | Description |
| --- | --- | --- | --- |
| Contract Name | `symbol` | https://futures.kraken.com/derivatives/api/v3/tickers | Ticker data |
| Underlying Asset | `base` | https://futures.kraken.com/derivatives/api/v3/instruments | Base asset |
| Quote Currency | `quote` | https://futures.kraken.com/derivatives/api/v3/instruments | Quote asset |
| Contract Type | `tag` | https://futures.kraken.com/derivatives/api/v3/tickers | Filter by tag |
| Funding Interval | Fixed | N/A | 1 hour default |
| Funding Rate | `fundingRate` | https://futures.kraken.com/derivatives/api/v3/tickers | **Note: Must divide by markPrice** |
| Index Price | `indexPrice` | https://futures.kraken.com/derivatives/api/v3/tickers | Underlying index price |
| Mark Price | `markPrice` | https://futures.kraken.com/derivatives/api/v3/tickers | Contract mark price |
| Open Interest | `openInterest` | https://futures.kraken.com/derivatives/api/v3/tickers | Total open interest |

**Important**: Kraken's `fundingRate` needs to be normalized by dividing by `markPrice` to get the actual funding rate percentage.

### Deribit Endpoints

|  | Response Body Tag | Endpoint | Description |
| --- | --- | --- | --- |
| Contract Name | `instrument_name` | [test.deribit.com/api/v2/public/get_instruments?currency=any&kind=future](https://test.deribit.com/api/v2/public/get_instruments?currency=any&kind=future) |  |
| Underlying Asset | `base_currency` | [test.deribit.com/api/v2/public/get_instruments?currency=any&kind=future](https://test.deribit.com/api/v2/public/get_instruments?currency=any&kind=future) |  |
| Margin | `quote_currency` | [test.deribit.com/api/v2/public/get_instruments?currency=any&kind=future](https://test.deribit.com/api/v2/public/get_instruments?currency=any&kind=future) |  |
| Contract Type | `settlement_period` | [test.deribit.com/api/v2/public/get_instruments?currency=any&kind=future](https://test.deribit.com/api/v2/public/get_instruments?currency=any&kind=future) |  |
| Funding Cycle |  |  |  |
| Funding Rate | `funding_8h` | [https://deribit.com/api/v2/public/ticker?instrument_name={}](https://deribit.com/api/v2/public/ticker?instrument_name=%7B%7D) | real time funding rate |
| Index Price | `index_price` | [https://deribit.com/api/v2/public/ticker?instrument_name={}](https://deribit.com/api/v2/public/ticker?instrument_name=%7B%7D) |  |
| Mark Price | `mark_price` | [https://deribit.com/api/v2/public/ticker?instrument_name={}](https://deribit.com/api/v2/public/ticker?instrument_name=%7B%7D) |  |
| Open Interest | `open_interest` | [https://deribit.com/api/v2/public/ticker?instrument_name={}](https://deribit.com/api/v2/public/ticker?instrument_name=%7B%7D) |  |