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
To enable Track Changes the new "Track Changes URL" field in the studio
Peer Assessment settings should be set the library file to be used.

A few things to keep in mind:
- Currently, the only supported library is ICE
- This setting is per problem, to allow granular control
- The file URL should ideally point to a CDN, as the file will get downloaded often
