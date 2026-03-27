<!-- BLOG-POST-LIST:START -->
- [Why Men Pull Away: 9 Toxic Signs He’s Shutting Down](https://understandman727.blogspot.com/2026/03/why-men-pull-away-9-toxic-signs-hes.html)
- [If he’s pulling away, don’t panic—follow this 5 step repair plan.](https://understandman727.blogspot.com/2026/03/if-hes-pulling-away-dont-panicfollow.html)
- [7 Anxious Attachment Patterns Driving Men Away &lpar;Fix Them&rpar;](https://understandman727.blogspot.com/2026/03/7-anxious-attachment-patterns-driving.html)
- [7 Toxic Patterns Women Ignore in Anxious Attachment](https://understandman727.blogspot.com/2026/03/7-toxic-patterns-women-ignore-in.html)
- [9 Toxic Anxious Attachment Behaviors](https://understandman727.blogspot.com/2026/03/blog-post.html)
<!-- BLOG-POST-LIST:END -->

## Automation

The blog roll above is refreshed exclusively by the [`scripts/python/update_readme.py`](scripts/python/update_readme.py) helper. This script is the single source of truth for updating the `<!-- BLOG-POST-LIST -->` block.

- Run it locally with `python scripts/python/update_readme.py --offline` to use the bundled sample feed when network access is restricted.
- In GitHub, the workflow at [`.github/workflows/update-readme.yml`](.github/workflows/update-readme.yml) runs the script hourly, on manual dispatch, and whenever the feed configuration at [`config/blogs.json`](config/blogs.json) changes so the list stays up to date.
- The previous third-party action (`blog-post-workflow.yml`) has been removed to avoid conflicting edits; the Python script-driven workflow described above is the only automation that updates the README.
