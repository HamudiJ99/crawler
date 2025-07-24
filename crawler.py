# crawler.py
import requests
from bs4 import BeautifulSoup
import json
from rdflib import Graph
import tkinter as tk
from tkinter import ttk, messagebox

CSV_URL = "https://url-backend-production-132c.up.railway.app/api/urls"

def fetch_urls():
    resp = requests.get(CSV_URL)
    resp.raise_for_status()
    return [line.strip().replace('"', '') for line in resp.text.splitlines() if line.strip()]

def crawl_and_convert(urls, progress_callback, output_callback):
    g = Graph()
    jsonld_count = 0
    found_jsonlds = []
    for idx, url in enumerate(urls):
        output_callback(f"Scanne: {url}")
        try:
            page = requests.get(url, timeout=10)
            soup = BeautifulSoup(page.text, "html.parser")
            found = False
            for tag in soup.find_all("script", type="application/ld+json"):
                output_callback("JSON-LD gefunden:")
                output_callback(tag.string)
                try:
                    data = json.loads(tag.string)
                    # Kontext ersetzen, falls nicht erreichbar
                    if "@context" in data and data["@context"].startswith("http"):
                        data["@context"] = {
                            "@vocab": "http://example.org/ftf-context#"
                        }
                    g.parse(data=json.dumps(data), format="json-ld")
                    jsonld_count += 1
                    found_jsonlds.append(tag.string)
                except Exception as rdf_err:
                    output_callback(f"Fehler beim Parsen/Umwandeln in RDF: {rdf_err}")
                found = True
            if not found:
                output_callback("Kein JSON-LD gefunden.")
        except Exception as e:
            output_callback(f"Fehler bei {url}: {e}")
        progress_callback(idx + 1, len(urls))
    if jsonld_count > 0:
        g.serialize(destination="output.owl", format="xml")
        output_callback(f"\n{jsonld_count} JSON-LD-Blöcke wurden als OWL (output.owl) gespeichert.")
    else:
        output_callback("\nKeine JSON-LD-Blöcke gefunden, nichts gespeichert.")
    return found_jsonlds

# --- GUI mit Tkinter ---
class CrawlerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("JSON-LD Crawler & OWL Generator")
        self.urls = []
        self.create_widgets()

    def create_widgets(self):
        frame = tk.Frame(self.root)
        frame.pack(padx=16, pady=16)

        tk.Label(frame, text="Indizierte URLs:").pack(anchor="w")
        self.url_listbox = tk.Listbox(frame, width=80, height=8)
        self.url_listbox.pack()

        self.progress = ttk.Progressbar(frame, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=8)

        self.start_btn = tk.Button(frame, text="Crawlen & OWL generieren", command=self.start_crawl)
        self.start_btn.pack(pady=4)

        self.output_text = tk.Text(frame, width=80, height=12, wrap="word")
        self.output_text.pack(pady=8)

        self.refresh_btn = tk.Button(frame, text="URLs aktualisieren", command=self.load_urls)
        self.refresh_btn.pack(pady=4)

        self.load_urls()

    def load_urls(self):
        try:
            self.urls = fetch_urls()
            self.url_listbox.delete(0, tk.END)
            for url in self.urls:
                self.url_listbox.insert(tk.END, url)
            self.output_text.insert(tk.END, f"{len(self.urls)} URLs geladen.\n")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Laden der URLs: {e}")

    def update_progress(self, value, maximum):
        self.progress["maximum"] = maximum
        self.progress["value"] = value
        self.root.update_idletasks()

    def output(self, text):
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)

    def start_crawl(self):
        self.output_text.delete(1.0, tk.END)
        if not self.urls:
            self.output("Keine URLs vorhanden.")
            return
        self.progress["value"] = 0
        found_jsonlds = crawl_and_convert(
            self.urls,
            self.update_progress,
            self.output
        )
        if found_jsonlds:
            messagebox.showinfo("Fertig", f"{len(found_jsonlds)} JSON-LD-Blöcke gefunden und als OWL gespeichert.")
        else:
            messagebox.showinfo("Fertig", "Keine JSON-LD-Blöcke gefunden.")

if __name__ == "__main__":
    root = tk.Tk()
    app = CrawlerGUI(root)
    root.mainloop()