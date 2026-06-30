import time
from playwright.sync_api import sync_playwright
from wikiSpeedRun.config import START_URL, TARGET_TITLE, MAX_STEPS

WIKI_BASE = "https://en.wikipedia.org"


def get_wiki_links(page) -> list[dict]:
    """Extract all internal Wikipedia article links from the current page."""
    links = page.eval_on_selector_all(
        "#mw-content-text a[href^='/wiki/']",
        """elements => elements
            .map(el => ({ href: el.getAttribute('href'), text: el.innerText.trim() }))
            .filter(l =>
                l.text &&
                !l.href.includes(':') &&
                !l.href.includes('#')
            )
        """
    )
    # Deduplicate by href
    seen = set()
    unique = []
    for link in links:
        if link["href"] not in seen:
            seen.add(link["href"])
            unique.append(link)
    return unique


def current_title(page) -> str:
    """Get the title of the current Wikipedia article."""
    return page.title().replace(" - Wikipedia", "").strip()


def run_agent():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # headless=False so you can watch it
        page = browser.new_page(
            user_agent=(
                "wikiSpeedRun/0.1 (https://github.com/wikiSpeedRun; "
                "educational bot) Python/Playwright"
            )
        )

        print(f"\n🚀 Starting at: {START_URL}")
        print(f"🎯 Target: {TARGET_TITLE}")
        print(f"🔢 Max steps: {MAX_STEPS}\n")

        page.goto(START_URL)
        visited = []
        steps = 0

        while steps < MAX_STEPS:
            title = current_title(page)
            visited.append(title)
            print(f"Step {steps}: 📄 {title}")
            print(f"Visited: {visited}")

            # Check if we've reached the target
            if TARGET_TITLE.lower() in title.lower():
                print(f"\n✅ Reached target in {steps} steps!")
                print(" → ".join(visited))
                break

            # Get all links on the page
            links = get_wiki_links(page)
            if not links:
                print("❌ No links found. Stopping.")
                break

            print(f"   Found {len(links)} links")
            '''
                TODO: Do a cosine similarity for the current link to that of the resultant link for each page,
                go to the page with the nearest similarity and move on until then
            '''

            word_embedding = word_to_embedding()
            target_words = set(TARGET_TITLE.lower().split())
            chosen = None

            for link in links:
                link_words = set(link["text"].lower().split())
                if link_words & target_words:  # intersection
                    print(f"link {link}")
                    chosen = link
                    print(f"   🎯 Matched target word in: '{link['text']}'")
                    break

            # Fallback: just pick the first link
            if not chosen:
                chosen = links[0]
                print(f"   ➡️  No match, following first link: '{chosen['text']}'")

            next_url = WIKI_BASE + chosen["href"]
            page.goto(next_url)
            time.sleep(0.5)  # be polite
            steps += 1

        else:
            print(f"\n❌ Did not reach target in {MAX_STEPS} steps.")
            print("Path taken: " + " → ".join(visited))

        input("\nPress Enter to close the browser...")
        browser.close()


def get_target_embedding(TARGET_TITLE):
    
if __name__ == "__main__":
    run_agent()