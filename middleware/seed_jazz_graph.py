from arango import ArangoClient
import os
import re
import time
import httpx


def _slug_key(value: str) -> str:
    raw = (value or "").strip().lower()
    raw = re.sub(r"[^a-z0-9]+", "_", raw)
    raw = raw.strip("_")
    return raw or "item"


def _download_standards() -> list[dict]:
    url = (os.getenv("JAZZ_STANDARDS_URL") or "").strip()
    if not url:
        return []
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()
    if isinstance(data, dict) and isinstance(data.get("standards"), list):
        data = data["standards"]
    if not isinstance(data, list):
        return []
    out: list[dict] = []
    for item in data:
        if isinstance(item, str):
            title = item.strip()
            if title:
                out.append({"title": title})
            continue
        if isinstance(item, dict):
            title = str(item.get("title") or item.get("name") or "").strip()
            if not title:
                continue
            cleaned = {"title": title}
            for k in ("composer", "composers", "year", "genre", "key", "album", "source"):
                if k in item and item.get(k) is not None:
                    cleaned[k] = item.get(k)
            out.append(cleaned)
    return out

def seed_jazz():
    # 1. Connect to ArangoDB
    # Since this runs in the middleware container, we use the service name 'arangodb'
    client = ArangoClient(hosts='http://arangodb:8529')
    
    # Wait for the DB to be ready
    db = None
    for i in range(10):
        try:
            sys_db = client.db('_system', username='root', password='')
            if not sys_db.has_database('jazz_vault'):
                sys_db.create_database('jazz_vault')
            db = client.db('jazz_vault', username='root', password='')
            print("Connected to ArangoDB!")
            break
        except Exception as e:
            print(f"Waiting for ArangoDB... ({e})")
            time.sleep(3)
    
    if not db:
        print("Could not connect to ArangoDB.")
        return

    # 2. Create the Graph and Collections
    if not db.has_graph('Jazz'):
        db.create_graph('Jazz')
    
    graph = db.graph('Jazz')
    
    if not db.has_collection('Musicians'):
        db.create_collection('Musicians')
    if not db.has_collection('Songs'):
        db.create_collection('Songs')
    
    # Edge collection
    if not graph.has_edge_definition('plays_on'):
        graph.create_edge_definition(
            edge_collection='plays_on',
            from_vertex_collections=['Musicians'],
            to_vertex_collections=['Songs']
        )
    
    musicians = db.collection('Musicians')
    songs = db.collection('Songs')
    plays_on = db.collection('plays_on')

    # 3. Sample Data: The Jazz Legends
    legends = [
        {"_key": "miles_davis", "name": "Miles Davis", "instrument": "Trumpet", "era": "Cool Jazz"},
        {"_key": "john_coltrane", "name": "John Coltrane", "instrument": "Saxophone", "era": "Hard Bop"},
        {"_key": "billie_holiday", "name": "Billie Holiday", "instrument": "Vocals", "era": "Vocal Jazz"},
        {"_key": "chet_baker", "name": "Chet Baker", "instrument": "Trumpet", "era": "West Coast Jazz"}
    ]
    
    standard_songs = [
        {"_key": "so_what", "title": "So What", "year": 1959, "album": "Kind of Blue"},
        {"_key": "blue_in_green", "title": "Blue in Green", "year": 1959, "album": "Kind of Blue"},
        {"_key": "naima", "title": "Naima", "year": 1959, "album": "Giant Steps"},
        {"_key": "strange_fruit", "title": "Strange Fruit", "year": 1939, "album": "Fine and Mellow"}
    ]

    downloaded = []
    try:
        downloaded = _download_standards()
        if downloaded:
            print(f"Downloaded {len(downloaded)} jazz standards.")
    except Exception as e:
        print(f"Jazz standards download failed, using built-in samples. ({e})")

    for m in legends:
        if not musicians.has(m["_key"]):
            musicians.insert(m)
    
    for s in standard_songs:
        if not songs.has(s["_key"]):
            songs.insert(s)

    if downloaded:
        used_keys: set[str] = set()
        for item in downloaded:
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            base_key = _slug_key(title)
            key = base_key
            n = 2
            while key in used_keys or songs.has(key):
                key = f"{base_key}_{n}"
                n += 1
            used_keys.add(key)
            doc = {"_key": key, "title": title}
            for k, v in item.items():
                if k in ("_key", "title"):
                    continue
                doc[k] = v
            songs.insert(doc)

    # 4. Relationships (The Graph Edges)
    relationships = [
        ("Musicians/miles_davis", "Songs/so_what"),
        ("Musicians/john_coltrane", "Songs/so_what"),
        ("Musicians/miles_davis", "Songs/blue_in_green"),
        ("Musicians/billie_holiday", "Songs/strange_fruit"),
        ("Musicians/john_coltrane", "Songs/naima")
    ]
    
    for f, t in relationships:
        edge_key = f"{f.split('/')[-1]}_{t.split('/')[-1]}"
        if not plays_on.has(edge_key):
            plays_on.insert({"_from": f, "_to": t, "_key": edge_key})

    print("Successfully seeded the Jazz Knowledge Graph! 🎷")

if __name__ == "__main__":
    seed_jazz()
