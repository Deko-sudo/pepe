# Emergency disable and rollback

Level 1 emergency disable is coordinated deployment configuration, never a live remote toggle:

1. Set `embedded_chart_kill_switch` to strict JSON `true` in the authoritative manifest.
2. Compile and atomically publish a new bundle.
3. Restart/reload API, Mini App Nginx, and wrapper Nginx as one unit.
4. Confirm all three use the new bundle digest.

The expected state is unavailable API capabilities/configuration with no wrapper/provider URL, parent `frame-src 'none'`, removed Mini App iframe after fresh capability refresh, and wrapper `503` chart routes before provider execution. Quote and candle behavior is unchanged.

Level 2 code rollback reverts the W5 deployment artifact while deploying a blocked bundle. It retains W4 isolation, does not touch databases, and performs no destructive operation. Production rollback is documented only; production remains blocked without written TradingView confirmation and separate W6/W7 approvals.
