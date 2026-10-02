# Deploy Haqdaar to a free Hugging Face Space (about 30 minutes)

## Before you upload (most important)
1. Open each official scheme page. Copy the official eligibility, documents and steps into `data/sources/<scheme>.md` (replace the SAMPLE text, set `checked_on`).
2. Correct `data/rules.json` to match the official text. Set `verified` to `true` and `checked_on` to today's date for each scheme you checked.
3. Check every entry in `data/official_domains.json`.
4. Run `python tests_core.py`, then `python app.py`, and try all three tabs on your own computer.
5. Add questions to `eval/questions.json` (aim for about 30) and run `python eval/run_eval.py`. Adjust `MAX_DISTANCE` if good questions are being rejected or bad ones accepted.

## Create the Space
1. Make a free account at huggingface.co and click New, then Space.
2. Name it `haqdaar`, choose the **Gradio** SDK, hardware **CPU basic (free)**, visibility **Public**.
3. The Space creates its own `README.md` with a settings header at the top. Keep that header. Paste the project README text below it.
4. Upload all the other files and folders (Files tab, then Add file, then Upload). Keep the same folder structure.
5. Wait for the build to finish (the first start is slow because models download).
6. Open the Space link in a private browser window and test all three tabs.

## Fill in the form
- Working link: your Space URL (huggingface.co/spaces/YOUR-NAME/haqdaar).
- Credentials: write "No login required. Public demo." Never put a real password in the form.

## Tips
- Free Spaces go to sleep when unused. Open the link a few minutes before you submit so it is awake.
- If voice fails on the free hardware, the app still works by typing. Say so in the README under Known limitations.
- Keep `USE_LLM` off on the free CPU unless you have tested it. It is slower and Urdu quality from small models can be weak.
