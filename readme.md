# ChainRift bot template
This template is prepared to fetch tickers from BitFinex and Poloniex 
based on the settings.

## Brief description
After subscribing to selected tickers, it sends a signal to process 
the current pair. Currently the implemented logic places orders for 
buy and/or sell side on ChainRift, limited by the amount set in 
settings per pair.

## Settings
In settings.py the following can set:

* the spread of the price from current bid/ask.
* WS API hosts
* tickers to track data for
* map tickers from BitFinex and Poloniex to ChainRift
* tickers to place orders for on ChainRift (with max amounts for buy
/sell side)
* ChainRift API id and key

## Dependencies
It has been tested to work with Python 3.5+

The application has the following dependencies:

* rsa
* pyasn1
* autobahn
* blinker
* asyncblink

Which can be installed using ```pip install -r dependencies.txt```

## How to run
Start the project by executing ```python start.py```

## Customization
In order to expand the functionality of the application you can modify
OrderManagement class in OrderLogic.py. OrderManagement.process_orders 
method is called with updated ticker data or, for upon retrieving CR 
balances with a specific command that triggers processing orders on all
selected pairs.

Behaviour can be changed in order to act on last price instead of 
modified bid/ask. The main logic for processing orders (placing and 
updating) happens in method OrderManagement.process_coinpair_orders().
Currently it checks if any of existing orders are outside of the 
permitted range and in case they're not it moves the order price-wise 
to a new randomly set price within range.

While orders are being generated they are stored in a ticker side 
specific variable OrderManagement.oafp. The orders are placed during 
processing (upon detecting that maximum allowable quantity has been 
used) and at the end of processing to push leftover actions.

Currently open orders and current balances can be used from 
ChainRiftData.balances and ChainRiftData.openOrders. It is not 
recommended to edit data in this class manually because the data is 
built using the subscriptions on balance and order changes.

## Features that might be added later

* deadman switch (WS API command for this is already available)
* Storing order and balance information persistently (in DB, 
currently it's only in memory)
* Updating orders upon disconnect (balances are refreshed upon disconnect)  
