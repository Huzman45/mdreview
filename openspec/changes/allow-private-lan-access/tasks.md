## 1. Explicit LAN binding

- [x] 1.1 Add `MDREVIEW_ALLOW_LAN` and a setting carrying the explicit opt-in
- [x] 1.2 Accept one concrete private IP while preserving the loopback default
- [x] 1.3 Reject wildcard, public, and hostname binds even with the opt-in
- [x] 1.4 Revalidate the bind immediately before uvicorn opens the socket
- [x] 1.5 Add `--allow-lan` to CLI operations and propagate it through autostart
- [x] 1.6 Print a security warning when serving outside loopback
- [x] 1.7 Document phone access and the unauthenticated-network trade-off
- [x] 1.8 Test accepted and refused addresses plus environment opt-in
- [x] 1.9 Run the full test and lint suite
- [x] 1.10 Bypass environment HTTP proxies for local and private-LAN API traffic
- [x] 1.11 Install the updated CLI and verify the live phone URLs
