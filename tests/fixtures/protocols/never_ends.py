"""A protocol that never finishes, to test that Provette gives up after its time limit."""

metadata = {"protocolName": "Never ends", "apiLevel": "2.11"}


def run(protocol):
    while True:
        pass
