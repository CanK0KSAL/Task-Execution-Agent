# Demo transcript (sample)

Abbreviated samples from the interactive CLI or the same flows as `uv run python main.py demo`. Tool names match the mock registry.

## Dentist: clarification, then book

**You:** Book me a dentist appointment next week after 5pm.  
**Agent:** Clarification (missing city). No tools run.

**You:** Warsaw  
**Agent:** Partial success — calendar check + search return options; blockers note confirmation required; `booking_service` not called.

**You:** book the first one  
**Agent:** Success — `booking_service` then `reminder_create`; booking panel + reminder panel.

## Coworking search

**You:** Find me 3 coworking spaces in Warsaw under $20/day.  
**Agent:** Success — `search_service` only; three options in the table.

## Prague trip

**You:** Plan a 2-day trip to Prague under 300 EUR.  
**Agent:** Success — `search_service`; summary mentions destination, duration, and budget.

## Cancel pending booking

**You:** Book me a dentist appointment in Warsaw next week after 5pm.  
**Agent:** Options + confirmation required.

**You:** cancel  
**Agent:** Success message that the pending action was canceled; no booking.

## Non-interactive demo

```bash
uv run python main.py demo
```

Prints each scenario, turns, tools called, and a line such as `8/8 scenarios passed basic checks.`
