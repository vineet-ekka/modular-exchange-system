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