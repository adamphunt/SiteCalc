# SiteCalc

Small, dependency-light calculators for home-improvement planning.

## Utilities

- **Deck layout:** evaluates repeating narrow/standard/wide board patterns, gaps,
  borders, and optional picture frames.
- **Lumber optimizer:** consumes existing scrap first, then packs cuts into the
  smallest available stock lengths while accounting for blade kerf.
- **Hex floor:** generates and validates a color-balanced L-shaped hex-tile layout.

Each utility has its own README with examples. Run the full test suite with:

```bash
python3 -m unittest discover -s lumber_optimizer -p 'test_*.py'
python3 -m unittest discover -s deck_layout -p 'test_*.py'
python3 -m unittest discover -s hex_floor -p 'test_*.py'
```

All layout dimensions are inches unless a CLI argument explicitly says otherwise.
