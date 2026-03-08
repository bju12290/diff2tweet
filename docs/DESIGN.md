# Automatic Social Media Posts

### General Notes

Feed project git commits, diffs, and a NOTES.md file to get candidate tweets output from an LLM.

NOTES.md is not assumed to be a dedicated notes file, it is a dedicated file for this tool that gives the user the ability to feed optional context to the LLM that would not be detectable in commits and diffs.

* CLI Command -> difftotweet
* Later: GitHub Actions -> User drops a YAML file into their repo so every time they merge to main a drafted tweet automatically drops into their slack/discord webhook (or alternatively a simpler output, like a direct file write to the repo)
* README as a Landing Page
  * HOOK: Side-by-side before and after image of a dry unreadable git diff next to a punchy engaging tweet the tool generated
  * Time-to-value: Installation command/quickstart immediately below the hook
* UI/Approval
  * Simple y/n in CLI
  * Thumbs-Up/Thumbs-Down in discord. Something similar in slack?
  * Save all tweets in a log with approval status (approved/denied), date, creation time, approval/denial time
  * We need to consider how we can save these tweets in a log without bloating peoples repos. Maybe a CLI command to delete all run artifacts (with y/n confirmation)
* BYO API Key. Configurable model.
* Config should be a YAML file, with a validator
* We will likely spend most of our time tweaking the output to ensure it produces valuable tweets and not "Pushed a new commit to main that optimizes stability!" I foresee this being the single biggest challenge.

# Design

**MVP Features**:

1. CLI tool: `diff2tweet path/to/diff_or_notes.txt`
2. Uses OpenAI API (default)
3. Outputs draft tweets to MD file and to log file
4. Simple approval mechanism (e.g., y/n prompt)


1. Milestone 1: CLI tool (Python) with:
   * `diff2tweet path/to/diff.md`
   * OpenAI API integration
   * Simple approval prompt (y/n)
2. Milestone 2: Add support for:
   * Local LLMs (via Ollama/LMStudio), Claude and Gemini integration
   * Git hook integration
3. GitHub Launch:
   * Repo name:`diff2tweet`
   * Tagline:*"Stop forgetting to tweet about your code wins"*
   * Target: 500+ stars in first month
4. Market > Show HN, Dev.to, Hashnode, Twitter
   * If interest is shown, push to integrate next steps
5. Github Actions Integration
   * User adds YAML file to repo -> every merge to main produces a new tweet candidate in MD (later slack and discord)
6. Slack & Discord Integration
   * Drafts sent to slack/discord. Approve/deny via UI interactions (emojis, thumbs up/thumbs down)
7. Automatic Tweeting After Approval (Optional Config)
   * Give users the ability to have the tool automatically post to X (and maybe threads later) if configured to do so.
8. Future thinking:
   * Visuals. Video and Images.

# Proposed config options

- model - The model name used by the API provider to select the model
- custom instructions - custom instructions to pass to the LLM
- forced hashtags - hashtags that will always be in the tweet
- character limit - use twitter defaults, but if the user wants let them uncap it
- output folder - folder where run artifacts live