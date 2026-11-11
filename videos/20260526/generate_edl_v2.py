import json
import re

# Ler a transcrição empacotada
with open('edit/takes_packed.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Extrair todos os ranges [start-end]
pattern = r'\[(\d+\.\d+)-(\d+\.\d+)\]'
matches = list(re.finditer(pattern, content))

ranges = []
for match in matches:
    start = float(match.group(1))
    end = float(match.group(2))
    ranges.append((start, end))

# Remover duplicatas e ordenar
ranges = sorted(set(ranges))

# Identificar gaps > 1.5s e criar "períodos a remover"
periods_to_remove = []
error_removal = (18.31, 21.62)  # "Não treinei isso"
periods_to_remove.append(error_removal)

for i in range(len(ranges) - 1):
    current_end = ranges[i][1]
    next_start = ranges[i + 1][0]
    gap = next_start - current_end
    if gap > 1.5:
        # Remover o gap da transição entre uma frase e outra
        # Colapsa para uma transição suave < 100ms
        periods_to_remove.append((current_end, next_start))

print(f"Total de ranges: {len(ranges)}")
print(f"\nPeríodos a remover: {len(periods_to_remove)}")
for p in periods_to_remove[:5]:
    print(f"  {p[0]:.2f}s → {p[1]:.2f}s")
if len(periods_to_remove) > 5:
    print(f"  ... e {len(periods_to_remove) - 5} mais")

# Filtrar ranges: manter apenas os que NÃO caem dentro de períodos a remover
edl_ranges = []
for start, end in ranges:
    keep = True
    for remove_start, remove_end in periods_to_remove:
        # Se este range está totalmente dentro de um período a remover, pular
        if start >= remove_start and end <= remove_end:
            keep = False
            break

    if keep:
        edl_ranges.append({"start": start, "end": end})

# Gerar EDL JSON
video_path = 'D:\\youtube\\video-use\\videos\\20260526\\2026-05-26 19-13-41.mp4'
edl = {
    "version": 1,
    "sources": {
        "main": video_path
    },
    "ranges": [
        {
            "source": "main",
            "start": r['start'],
            "end": r['end'],
            "beat": "content"
        }
        for r in edl_ranges
    ],
    "grade": "none",
    "overlays": [],
    "subtitles": None
}

# Calcular duração total
total_duration = sum(r['end'] - r['start'] for r in edl_ranges)
edl['total_duration_s'] = total_duration

print(f"\n=== RESULTADO FINAL ===")
print(f"Ranges mantidos: {len(edl_ranges)}/{len(ranges)}")
print(f"Duração original: 19m 05.9s (1145.9s)")
print(f"Duração final: {int(total_duration // 60)}m {total_duration % 60:.1f}s ({total_duration:.1f}s)")
reduction = 1145.9 - total_duration
reduction_pct = (1 - total_duration/1145.9)*100
print(f"Redução: {reduction:.1f}s ({reduction_pct:.1f}%)")

# Salvar EDL
with open('edit/edl.json', 'w', encoding='utf-8') as f:
    json.dump(edl, f, indent=2)

print("\n✓ EDL salvo em edit/edl.json")
