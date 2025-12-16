from pathlib import Path

class Visualizer:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.report_path = output_dir / "report.html"

    def generate(self, groups: list, total_websites: int):
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<title>Logo Similarity Report</title>",
            "<style>",
            "body { font-family: sans-serif; padding: 20px; background: #f5f5f5; }",
            ".header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }",
            ".group { background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }",
            ".group-header { border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 15px; font-weight: bold; color: #333; display: flex; justify-content: space-between; }",
            ".grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; }",
            ".card { text-align: center; border: 1px solid #eee; padding: 10px; border-radius: 4px; transition: transform 0.2s; }",
            ".card:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }",
            ".card img { max-width: 100%; height: 80px; object-fit: contain; margin-bottom: 8px; }",
            ".domain { font-size: 11px; color: #666; word-break: break-all; }",
            ".meta { color: #666; font-size: 14px; margin-top: 5px; }",
            "</style>",
            "</head>",
            "<body>",
            f"<div class='header'><h1>Logo Similarity Results</h1><div class='meta'>Processed {total_websites} websites • Found {len(groups)} groups</div></div>"
        ]

        for group in groups:
            html.append(f"<div class='group'>")
            html.append(f"<div class='group-header'><span>{group[0]['group_id'].upper()}</span> <span>Size: {group[0]['size']}</span></div>")
            html.append(f"<div class='grid'>")
            
            for item in group[0]['websites']:
                url = item['url']
                safe_name = url.replace("https://", "").replace("http://", "").replace("/", "_").replace(":", "_").replace("?", "_")
                img_path = f"images/{safe_name}.jpg"
                
                html.append(f"""
                <div class='card'>
                    <a href='{img_path}' target='_blank'><img src='{img_path}' loading='lazy' onerror="this.src='https://placehold.co/100x80?text=No+Image'"></a>
                    <div class='domain'><a href='{url}' target='_blank' style='color: inherit; text-decoration: none;'>{url}</a></div>
                </div>
                """)
            
            html.append("</div></div>")

        html.append("</body></html>")
        self.report_path.write_text("\n".join(html), encoding="utf-8")
        return self.report_path