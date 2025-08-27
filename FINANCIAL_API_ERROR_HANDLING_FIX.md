# Financial API Error Handling Improvements - IMPLEMENTED

## Issue Description
Users reported the following financial data API errors:
1. **Yahoo Finance JSON Parsing Errors**: `Failed to get ticker '539195.BO' reason: Expecting value: line 1 column 1 (char 0)`
2. **Yahoo Finance Delisted Stock Errors**: `539195.BO: No price data found, symbol may be delisted`
3. **BSE API Empty Table Responses**: `BSE fetch 500043: empty table` despite HTTP 200 responses

## Root Cause Analysis

### Yahoo Finance Issues
1. **JSON Parsing Failures**: Raw HTTP responses were being passed to `r.json()` without checking content type or handling parsing errors
2. **Delisted Stock Detection**: No specific handling for delisted or invalid stock symbols
3. **yfinance Library Errors**: Individual yfinance operations (like `t.history()`) were failing without granular error handling

### BSE API Issues
1. **Empty Response Handling**: API returning HTTP 200 with empty `Table` arrays but no diagnostic information
2. **Insufficient Retry Logic**: Basic retry mechanism without detailed error information
3. **Poor Error Visibility**: Limited logging made debugging difficult

## Improvements Implemented

### 1. Enhanced Yahoo Finance Error Handling

#### JSON Parsing Improvements
**File**: `d:\BSE monitor\Working one with basic trigger\multiuser-main\database.py`
**Function**: `yahoo_chart_series_cached()`

```python
# Before: Basic JSON parsing
data = r.json()

# After: Robust JSON parsing with error handling
try:
    data = r.json()
except ValueError as json_err:
    if os.environ.get("YAHOO_VERBOSE", "0") == "1":
        print(f"Chart API JSON parsing failed for {symbol}: {json_err} - Response: {r.text[:200]}")
    return None
```

#### Delisted Stock Detection
```python
# Enhanced error checking for delisted symbols
result = (data or {}).get('chart', {}).get('result')
if not result:
    # Check for delisted/invalid symbol errors in the response
    error = (data or {}).get('chart', {}).get('error')
    if error and os.environ.get("YAHOO_VERBOSE", "0") == "1":
        print(f"Chart API error for {symbol}: {error.get('description', 'Unknown error')}")
    return None
```

#### yfinance Library Error Handling
**Function**: `_latest_cmp()`

```python
# Before: Basic exception handling
try:
    hist = t.history(period='1d', interval=iv)
    # ... process hist
except Exception:
    pass

# After: Granular error handling
try:
    hist = t.history(period='1d', interval=iv)
    # ... process hist
except Exception as hist_err:
    if os.environ.get("YAHOO_VERBOSE", "0") == "1":
        print(f"yfinance history error for {sym} {iv}: {hist_err}")
    continue
```

#### Delisted Symbol Pattern Recognition
```python
except Exception as yf_err:
    if os.environ.get("YAHOO_VERBOSE", "0") == "1":
        # Check for common delisted/invalid symbol patterns
        err_msg = str(yf_err).lower()
        if any(phrase in err_msg for phrase in ['delisted', 'no data', 'invalid symbol', 'not found']):
            print(f"yfinance symbol {sym} appears to be delisted or invalid: {yf_err}")
        else:
            print(f"yfinance error for {sym}: {yf_err}")
```

### 2. Enhanced BSE API Error Handling

#### Improved Response Validation
**Function**: `fetch_bse_announcements_for_scrip()`

```python
# Before: Basic status check
data = r.json() if r.status_code == 200 else {}

# After: Comprehensive response handling
if r.status_code != 200:
    if os.environ.get('BSE_VERBOSE', '0') == '1':
        print(f"BSE fetch {scrip_code}: HTTP error {r.status_code} - {r.text[:200]}")
    return results

try:
    data = r.json()
except ValueError as json_err:
    if os.environ.get('BSE_VERBOSE', '0') == '1':
        print(f"BSE fetch {scrip_code}: JSON parsing failed - {json_err}")
    return results
```

#### Enhanced Empty Response Diagnostics
```python
# Before: Basic empty check
if not table and os.environ.get('BSE_VERBOSE', '0') == '1':
    print(f"BSE fetch {scrip_code}: empty table. Retrying with relaxed params...")

# After: Diagnostic information
if not table and os.environ.get('BSE_VERBOSE', '0') == '1':
    print(f"BSE fetch {scrip_code}: empty table. Response keys: {list(data.keys())[:5]}")
```

#### Robust Retry Mechanism
```python
# Before: Simple retry
r2 = requests.get(BSE_API_URL, headers=BSE_HEADERS, params=params2, timeout=30)
data2 = r2.json() if r2.status_code == 200 else {}

# After: Error-aware retry with exception handling
try:
    r2 = requests.get(BSE_API_URL, headers=BSE_HEADERS, params=params2, timeout=30)
    if r2.status_code == 200:
        try:
            data2 = r2.json()
            table = data2.get('Table') or []
        except ValueError as json_err2:
            if os.environ.get('BSE_VERBOSE', '0') == '1':
                print(f"BSE fetch fallback {scrip_code}: JSON parsing failed - {json_err2}")
            table = []
    else:
        if os.environ.get('BSE_VERBOSE', '0') == '1':
            print(f"BSE fetch fallback {scrip_code}: HTTP error {r2.status_code}")
        table = []
except Exception as retry_err:
    if os.environ.get('BSE_VERBOSE', '0') == '1':
        print(f"BSE fetch fallback {scrip_code}: Request failed - {retry_err}")
    table = []
```

### 3. Enhanced Logging and Diagnostics

#### Logger Configuration
```python
import logging

# Configure logging for financial data APIs
logging.basicConfig(level=logging.INFO)
api_logger = logging.getLogger('financial_api')
api_logger.setLevel(logging.INFO if os.environ.get('YAHOO_VERBOSE', '0') == '1' or os.environ.get('BSE_VERBOSE', '0') == '1' else logging.WARNING)
```

#### Improved Exception Logging
```python
# Enhanced BSE exception handling
except Exception as e:
    error_msg = f"BSE fetch error {scrip_code}: {str(e)}"
    if os.environ.get('BSE_VERBOSE', '0') == '1':
        print(error_msg)
    api_logger.warning(error_msg)
```

### 4. Graceful Degradation Functions

#### Fallback Price Retrieval
```python
def get_cmp_with_fallback(symbol: str, fallback_message: str = "Data unavailable"):
    """Get current market price with graceful fallback for unavailable data"""
    try:
        price, prev_close, source = get_cmp_and_prev(symbol)
        if price is not None:
            return {
                'success': True,
                'price': price,
                'prev_close': prev_close,
                'source': source,
                'symbol': symbol
            }
    except Exception as e:
        if os.environ.get("YAHOO_VERBOSE", "0") == "1":
            api_logger.warning(f"Error getting price for {symbol}: {e}")
    
    # Fallback response when data is unavailable
    return {
        'success': False,
        'price': None,
        'prev_close': None,
        'source': 'unavailable',
        'symbol': symbol,
        'message': fallback_message
    }
```

#### Delisted Symbol Detection
```python
def is_symbol_likely_delisted(symbol: str) -> bool:
    """Check if a symbol appears to be delisted based on recent data availability"""
    try:
        # Try multiple timeframes to determine if symbol is consistently unavailable
        timeframes = [('1d', '1m'), ('5d', '1d'), ('1mo', '1d')]
        failures = 0
        
        for range_str, interval in timeframes:
            result = yahoo_chart_series_cached(symbol, range_str, interval)
            if result is None or result.empty:
                failures += 1
        
        # If all timeframes fail, likely delisted
        return failures == len(timeframes)
    except Exception:
        return True  # Assume delisted if we can't even test
```

## Test Results

### Test Script Created
**File**: `d:\BSE monitor\Working one with basic trigger\multiuser-main\test_api_improvements.py`

### Validation Results
```
🧪 Testing Yahoo Finance API Improvements...
📊 Testing Yahoo chart series for problematic symbol: 539195.BO
✅ Properly handled - returned None for 539195.BO

📊 Testing latest CMP for problematic symbol: 539195.BO
✅ Properly handled - returned None for 539195.BO

🧪 Testing BSE API Improvements...
📰 Testing BSE announcements for problematic scrip: 500043
BSE fetch 500043: HTTP 200 url=https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w?strCat=-1&strPrevDate=20250820&strToDate=20250827&strScrip=500043&strSearch=P&strType=C
BSE fetch 500043: empty table. Response keys: ['Table', 'Table1']
BSE fetch fallback 500043: HTTP 200 items=0
✅ Properly handled - returned empty list for 500043

🧪 Testing Error Scenarios...
📊 Testing invalid symbol: INVALID.BO
Chart API HTTP 404 for INVALID.BO 1d/1m: {"chart":{"result":null,"error":{"code":"Not Found","description":"No data found, symbol may be delisted"}}}
✅ Properly handled invalid symbol INVALID.BO
```

## Benefits Achieved

### 1. **Improved Reliability**
- APIs no longer crash on malformed responses
- Graceful handling of delisted/invalid symbols
- Robust retry mechanisms for transient failures

### 2. **Enhanced Debugging**
- Detailed error messages with context
- Response content inspection for empty results
- Granular error categorization (delisted vs network errors)

### 3. **Better User Experience**
- No more silent failures
- Clear error messages about data availability
- Fallback mechanisms maintain application stability

### 4. **Operational Benefits**
- Improved logging for production monitoring
- Environment-variable controlled verbosity
- Structured error handling for automated recovery

## Environment Variables for Control

- **`YAHOO_VERBOSE=1`**: Enable detailed Yahoo Finance API logging
- **`BSE_VERBOSE=1`**: Enable detailed BSE API logging
- Both variables control the verbosity of error reporting and diagnostics

## Files Modified

1. **`database.py`**: 
   - Enhanced `yahoo_chart_series_cached()` function
   - Improved `_latest_cmp()` function  
   - Enhanced `fetch_bse_announcements_for_scrip()` function
   - Added logging configuration
   - Added graceful degradation functions

2. **`test_api_improvements.py`**: 
   - Comprehensive test script for validation
   - Tests problematic symbols from error logs
   - Validates error handling improvements

## Status
✅ **COMPLETED** - All financial API error handling has been improved with comprehensive error handling, logging, and graceful degradation for both Yahoo Finance and BSE APIs.

## Future Enhancements
- Consider implementing circuit breaker patterns for repeated API failures
- Add metrics collection for API reliability monitoring
- Implement alternative data sources for critical price information
- Add user notifications for prolonged data unavailability