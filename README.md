# Xiaomi Dreame 1C Vacuum Integration

Custom component for Xiaomi Dreame vacuum 1C (dreame.vacuum.mc1808).

Using https://github.com/rytilahti/python-miio for the protocol.

# Installation:
- Manually: add the "xiaomi_vacuum" folder to the /config/custom_components folder;
- With HACS: go in HACS, click on Integrations, click on the three little dots at top of the screen and selection "custom repositories", add this github url, select "Integration" as repository, and click ADD. Then go to the Integrations tab of HACS, and install the "Xiaomi 1C STYTJ01ZHM" integration.

### Code to add to configuration.yaml:

```
vacuum:
  - platform: xiaomi_vacuum
    host: <ip>
    token: "<token>"
    name: <name>
    unique_id: vacuum.<name>
```

To retrieve the token, follow the default integration <a href="https://www.home-assistant.io/integrations/vacuum.xiaomi_miio/#retrieving-the-access-token">instructions</a>.

Works with https://github.com/denysdovhan/vacuum-card
