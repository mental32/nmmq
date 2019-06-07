# Merlin

> "The client application that lets you build virtual networks and deploy services over them."


Merlin is a client side application that operates parasitically over much heavier services (discord, slack, etc).

Alternatively merlin supports running in "raw" mode (the serverside) if you dont want to get in trouble with the fuzz.

The pitch:

 - Its a poor mans solution to server or database hosting.
 - Designed for building "decentralised" apps
 - Easily extendable with the inbuilt framework.
 - Comes with a batteries included approach.

## Example

1) Git clone this repostory
2) run `sudo make install`
3) Now you can run the example: `merlin ./examples/simple_rtcp_shell`

> I highly suggest editing the configuration file before running it.
>
> Specifically changing the `inbound`, `token` and possibly `bot` settings depending on the account.
