.. _trackchanges:

############
TrackChanges
############


Overview
--------

In this document, we describe the use of Track Changes.

This feature allows the use of the ICE Track Changes js library in ORA2.


Configuration
-------------

To enable Track Changes, your edx_platform instance must have a the
ORA2_TRACK_CHANGES_URL key set to a valid URL for the New York Times's "ICE"
library. Furthermore, the "Track Changes" setting must be checked in the Peer
Assessment configuration display in Studio.

A few things to keep in mind:
- Currently, the only supported library is ICE
- If the sitewide setting is disabled, use of the Track Changes feature is
  disabled across the board.
- The file URL should ideally point to a CDN, as the file will get downloaded often
