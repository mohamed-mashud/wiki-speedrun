import time
import numpy as np
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from wikiSpeedRun.config import START_URL, TARGET_TITLE, MAX_STEPS
from sentence_transformers import SentenceTransformer
from numpy.linalg import norm

WIKI_BASE = "https://en.wikipedia.org"
MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def get_wiki_links(page) -> list[dict]:
    """Extract all internal Wikipedia article links from the current page."""
    links = page.eval_on_selector_all(
        "#mw-content-text a[href]",
        """elements => elements
            .map(el => {
                const url = new URL(el.href);  // el.href resolves to an absolute URL
                return { host: url.hostname, path: url.pathname, hash: url.hash, text: el.innerText.trim() };
            })
             .filter(l =>
                l.host === 'en.wikipedia.org' &&
                l.path.startsWith('/wiki/') &&
                l.text &&
                !l.path.includes(':') &&
                !l.hash
            )
            .map(l => ({ href: l.path, text: l.text }))
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


def current_path(page) -> str:
    """Get the current article's '/wiki/...' path (matches link href format)."""
    return urlparse(page.url).path


def run_agent():
    with sync_playwright() as p:
        target_word_embedding = get_word_embeddings(TARGET_TITLE)
        browser = p.chromium.launch(headless=False)  
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
        visited = {current_path(page)}
        path = []
        steps = 0

        while steps < MAX_STEPS:
            title = current_title(page)
            path.append(title)
            print(f"Step {steps}: 📄 {title}")
            # print(f"Visited: {path}")

            # Check if we've reached the target
            if TARGET_TITLE.lower() == title.lower():
                print(f"\n✅ Reached target in {steps} steps!")
                print(" → ".join(path))
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

            link_texts = [link["text"] for link in links]
            embedded_links = get_word_embeddings(link_texts)
            chosen = get_best_embedded_link(visited, embedded_links, links, target_word_embedding)

            # Fallback: just pick the first link
            if not chosen:
                chosen = links[0]
                print(f"   ➡️  No match, following first link: '{chosen['text']}'")

            visited.add(chosen["href"])
            next_url = WIKI_BASE + chosen["href"]
            page.goto(next_url)
            # time.sleep(0.5)
            steps += 1

        else:
            print(f"\n❌ Did not reach target in {MAX_STEPS} steps.")
            print("Path taken: " + " → ".join(path))

        input("\nPress Enter to close the browser...")
        browser.close()

def get_word_embeddings(word : str | list[str]):
    return MODEL.encode(word, convert_to_numpy=True, normalize_embeddings=True)

def get_best_embedded_link(visited, embedded_links, links, target_embedding):
    max_val = -1
    best_embedded_link = None

    for link_indx in range(0, len(embedded_links)):
        link = links[link_indx]
        if link["href"] not in visited:
            curr_val = cosine_similarity(target_embedding, embedded_links[link_indx])
            if curr_val > max_val:
                max_val = curr_val
                best_embedded_link = link
    
    if best_embedded_link is None:
        print("=========All links visited, picking first unvisited link==========")
        for link in links:
            if link["href"] not in visited:
                best_embedded_link = link
                break

    return best_embedded_link

def cosine_similarity(embedding1, embedding2):
    return np.dot(embedding1, embedding2) / (norm(embedding1) * norm(embedding2))

if __name__ == "__main__":
    run_agent()