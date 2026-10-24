"""Focus watcher: a small separate process that sees which app (and which site) is in front.

Claude Code can't see other apps, so this watches the frontmost app during a work block and
taps the wrist on a rabbit hole (distraction rule) or a long stretch without a break (break rule).
Privacy: only the app name and the site's domain are ever kept. Never a window title, page
title or full URL.
"""
