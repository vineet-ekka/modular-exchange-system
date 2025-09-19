# WebSocket Architecture Brief for Live Funding Rate Data

## Executive Summary

### Current State
- **Polling-based system**: REST API calls every 30 seconds
- **Sequential collection**: Staggered delays to manage rate limits
- **Batch processing**: All contracts updated together
- **Z-score calculation**: Triggered after batch updates

### Proposed WebSocket Approach
- **Real-time streaming**: Continuous data flow (1-3 second updates)
- **Persistent connections**: Single connection per exchange
- **Event-driven updates**: Process data as it arrives
- **Instant Z-score calculations**: Sub-second statistical updates

### Key Benefits
- **Latency reduction**: From 30 seconds to <1 second
- **API efficiency**: 80-90% reduction in REST calls
- **Real-time monitoring**: Instant funding rate changes
- **Better rate limit management**: WebSocket doesn't count against REST limits

## WebSocket Availability by Exchange

### Binance ✅ Full Support
- **Endpoints**:
  - USD-M: `wss://ws-fapi.binance.com/ws-fapi/v1`
  - COIN-M: `wss://ws-dapi.binance.com/ws-dapi/v1`
- **Stream**: `markPriceUpdate` event
- **Data**: Includes funding rate (`r`), next funding time (`T`)
- **Frequency**: Updates every 1-3 seconds

### KuCoin ✅ Event-Based Support
- **Topic**: `/contract/announcement`
- **Events**: `funding.begin` and `funding.end`
- **Data**: Funding rate, timestamp, symbol
- **Frequency**: At funding intervals (4h/8h)

### Hyperliquid ✅ Comprehensive Support
- **Endpoint**: `wss://api.hyperliquid.xyz/ws`
- **Streams**: `WsUserFundings`, market data streams
- **Limits**: 1000 subscriptions per IP
- **Frequency**: Real-time as changes occur

### Backpack ✅ Likely Support
- **Endpoint**: `wss://ws.backpack.exchange`
- **Stream**: `markprice.<symbol>`
- **Data**: Expected to include funding rate (mirrors REST)
- **Frequency**: Hourly funding updates (24x per day)

## Architecture Transformation

### Data Flow Evolution

**Current Flow**:
```
Timer (30s) → REST API → Rate Limiter → Database → Z-Score Batch → Update
```

**WebSocket Flow**:
```
WebSocket Stream → Message Queue → Processing → Database → Z-Score Real-time
    (continuous)      (buffer)      (instant)    (async)    (cached stats)
```

### Key Architectural Changes

1. **Connection Management**
   - Persistent WebSocket connections per exchange
   - Automatic reconnection with exponential backoff
   - Heartbeat/ping-pong to maintain connections

2. **Message Processing**
   - Message queue for buffering incoming data
   - Deduplication of duplicate messages
   - Timestamp-based ordering

3. **Data Storage Strategy**
   - Separate stream table for real-time updates
   - Periodic consolidation to historical tables
   - Hybrid approach: WebSocket for real-time, REST for historical

## Z-Score Calculation Strategy

### Current Approach
- Fetches 30-day historical data per calculation
- Calculates statistics on-demand
- Updates all contracts in batch
- Database-heavy operations

### Streaming Approach

#### Cached Statistics Model
- **Historical statistics cached**: Mean and std_dev refreshed hourly
- **Real-time calculation**: Z = (current_rate - cached_mean) / cached_std_dev
- **Memory requirement**: ~200KB for 1,260 contracts
- **Performance**: <1ms per Z-score calculation

#### Update Strategies

**Zone-Based Priority**:
- **High Activity** (|Z| > 2.0): Immediate updates
- **Normal Activity** (|Z| ≤ 2.0): Batch every 5 seconds
- **Stable Contracts**: Update statistics hourly

**Trigger Conditions**:
- Significant rate change (>10% movement)
- Crossing Z-score thresholds (±2.0, ±3.0)
- Time-based batch processing (5-second intervals)

## Implementation Considerations

### Connection Reliability
- **Primary**: WebSocket streaming
- **Fallback**: REST API polling
- **Health monitoring**: Connection status tracking
- **Auto-recovery**: Seamless failover mechanism

### Message Handling
- **Buffering**: Queue incoming messages
- **Ordering**: Handle out-of-sequence messages
- **Deduplication**: Prevent duplicate processing
- **Validation**: Verify data integrity

### Performance Optimization
- **Connection pooling**: Reuse WebSocket connections
- **Message batching**: Process in micro-batches
- **Async processing**: Non-blocking operations
- **Resource limits**: Cap memory usage for buffers

### Data Consistency
- **Reconciliation**: Periodic REST validation
- **Gap detection**: Identify missing data
- **Historical alignment**: Ensure continuity
- **Audit trail**: Log all updates

## Benefits Analysis

### Performance Improvements
| Metric | Current (REST) | WebSocket | Improvement |
|--------|---------------|-----------|-------------|
| Update Latency | 30 seconds | <1 second | 30x faster |
| API Calls/Hour | 480 per exchange | ~10 (heartbeat) | 98% reduction |
| Z-Score Latency | 30-60 seconds | <1 second | 60x faster |
| Data Freshness | 30-second old | Real-time | Instant |

### Resource Trade-offs
| Resource | Current | WebSocket | Impact |
|----------|---------|-----------|--------|
| Network Bandwidth | Burst every 30s | Continuous low | More stable |
| CPU Usage | Spikes every 30s | Distributed | Smoother |
| Memory | Low (~50MB) | Medium (~200MB) | +4x increase |
| Complexity | Simple polling | Event-driven | Higher |
| Reliability | REST fallback easy | Requires monitoring | More complex |

## Risk Mitigation

### Technical Risks
- **Connection drops**: Automatic reconnection with backoff
- **Message overflow**: Rate limiting and buffering
- **Data inconsistency**: REST reconciliation checks
- **Memory leaks**: Proper cleanup and limits

### Operational Risks
- **Exchange API changes**: Modular design for easy updates
- **Rate limit changes**: Adaptive throttling
- **WebSocket unavailability**: Seamless REST fallback
- **Data gaps**: Historical backfill capability

## Migration Strategy

### Phase 1: Hybrid Operation
- Keep REST polling active
- Add WebSocket as supplementary
- Compare data for validation
- Monitor performance metrics

### Phase 2: WebSocket Primary
- WebSocket becomes primary source
- REST for historical and backup
- Reduced polling frequency
- Enhanced monitoring

### Phase 3: Full Optimization
- Cached statistics implementation
- Real-time Z-score calculations
- Dashboard WebSocket integration
- Complete system optimization

## Success Metrics

### Technical Metrics
- WebSocket uptime >99.9%
- Message processing latency <100ms
- Z-score calculation time <10ms
- Memory usage <500MB

### Business Metrics
- Data freshness <1 second
- API cost reduction >80%
- System reliability maintained
- User experience improved

## Conclusion

WebSocket implementation offers significant advantages for real-time funding rate monitoring:

**Pros**:
- Near-instant data updates
- Dramatic reduction in API load
- Better scalability for more exchanges
- Enhanced user experience with real-time data

**Cons**:
- Increased system complexity
- Higher memory requirements
- More sophisticated error handling needed
- Requires careful monitoring

**Recommendation**: Implement WebSocket streaming with a phased approach, starting with Binance and Hyperliquid (most mature APIs), while maintaining REST as fallback. This provides immediate benefits while managing risk through gradual migration.