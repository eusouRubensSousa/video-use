import json
import re

# Ler a transcrição empacotada
with open('edit/takes_packed.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Extrair todos os ranges [start-end] e seus tempos
pattern = r'\[(\d+\.\d+)-(\d+\.\d+)\]'
matches = list(re.finditer(pattern, content))

ranges = []
for match in matches:
    start = float(match.group(1))
    end = float(match.group(2))
    ranges.append((start, end))

# Remover duplicatas e ordenar
ranges = sorted(set(ranges))

# Identificar gaps > 1.5s
print(f"Total de ranges encontrados: {len(ranges)}")
print("\n=== GAPS > 1.5s ===")
gaps_to_remove = []
for i in range(len(ranges) - 1):
    current_end = ranges[i][1]
    next_start = ranges[i + 1][0]
    gap = next_start - current_end
    if gap > 1.5:
        gaps_to_remove.append((current_end, next_start, gap))
        print(f"Gap: {current_end:.2f}s → {next_start:.2f}s = {gap:.2f}s")

# Remover ranges que estão em gaps > 1.5s
# Estratégia: mantém um range se ele não está completamente dentro de um gap
edl_ranges = []
for start, end in ranges:
    # Não remover se está dentro de um gap > 1.5s
    inside_big_gap = False

    # Verificar especialmente a seção de "Não treinei isso" (18.31-21.62)
    if start >= 18.31 and end <= 21.62:
        inside_big_gap = True
        print(f"→ Removendo por ser erro de gravação: [{start:.2f}-{end:.2f}]")

    if not inside_big_gap:
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
            "beat": "content",
            "reason": "kept"
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

print(f"\n=== RESULTADO ===")
print(f"Total de ranges a manter: {len(edl_ranges)}")
print(f"Duração original: ~19m 05.9s (1145.9s)")
print(f"Duração após remoção: {int(total_duration // 60)}m {total_duration % 60:.1f}s ({total_duration:.1f}s)")
print(f"Redução: {1145.9 - total_duration:.1f}s (~{(1 - total_duration/1145.9)*100:.1f}%)")

# Salvar EDL
with open('edit/edl.json', 'w', encoding='utf-8') as f:
    json.dump(edl, f, indent=2)

print("\n✓ EDL salvo em edit/edl.json")
