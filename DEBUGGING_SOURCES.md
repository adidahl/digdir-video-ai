# Debugging Video Source References

## Problem

Kada korisnik postavi pitanje poput "Var der en person som heter Marting og hvor jobber han?", sistem može dati tačan odgovor, ali video linkovi i timestampi koji se vraćaju su pogrešni - ne pokazuju na pravi segment gde se informacija nalazi.

## Uzrok Problema

Problem nastaje zbog načina kako LightRAG radi sa "mix" modom:

1. **Knowledge Graph Synthesis**: LightRAG u "mix" modu kombinuje knowledge graph i vector retrieval. Knowledge graph može sintetizovati informacije iz više segmenata i čuvati ih kao entitete u grafu.

2. **Metadata Header Mismatch**: Kada LightRAG vraća kontekst sa `only_need_context=True`, metadata headeri (poput `[video_id=X;start=Y;end=Z]`) mogu biti iz segmenata koji su semantički slični, ali ne i stvarni izvori informacije.

3. **Context vs Answer Mismatch**: Metadata headeri u vraćenom kontekstu mogu biti iz jednog segmenta, dok je stvarni odgovor sintetizovan iz više segmenata preko knowledge grafa.

## Rešenje

Implementirane su sledeće izmene u `backend/app/api/chat.py`:

### 1. Dual-Mode Source Extraction

Koristimo dva načina za izvlačenje izvora:
- **Vector-only mode (`naive`)**: Koristi se za izvlačenje izvora jer bolje čuva tačne metadata headere iz originalnih segmenata
- **Mix mode**: Koristi se za generisanje odgovora jer daje bolji kvalitet odgovora pomoću knowledge grafa

```python
# Vector mode za tačne metadata headere
lightrag_context_vectors = await lightrag_service.search_async(
    mode="naive",  # Vector-only - čuva tačne metadata headere
    only_need_context=True
)

# Mix mode za kompletan retrieval
lightrag_context_mix = await lightrag_service.search_async(
    mode="mix",  # Knowledge graph + vector
    only_need_context=True
)

# Kombinujemo oba za izvlačenje izvora
combined_context = lightrag_context_vectors + "\n\n" + lightrag_context_mix
```

### 2. Validacija Segmenata

Dodata je validacija da proveri da li segmenti stvarno sadrže relevantne informacije:

```python
# Proverava da li segment sadrži ključne reči iz upita
query_keywords = [word.lower() for word in query.split() if len(word) > 2]
has_relevant_content = any(keyword in segment.text.lower() for keyword in query_keywords)
```

### 3. Poboljšano Matchovanje Segmenata

- Pokušava prvo da pronađe segment po `start_time` (sa tolerancijom ±0.1s)
- Ako to ne uspe, pokušava da pronađe po `segment_id` iz metadata headera
- Ako ni to ne uspe, koristi fallback - bilo koji segment iz tog videa (sa upozorenjem)

### 4. Validacija Odgovora vs Izvori

Proverava da li odgovor pominje entitete (npr. imena osoba) koje su u izvorima:

```python
potential_names = re.findall(r'\b[A-ZÆØÅ][a-zæøå]+(?:\s+[A-ZÆØÅ][a-zæøå]+)*\b', query)
# Proverava da li izvori sadrže ova imena
```

### 5. Poboljšano Logovanje

Dodato je detaljno logovanje za debugging:
- Puni LightRAG kontekst (prvih 2000 karaktera)
- Metadata headeri iz oba moda
- Validacioni rezultati za svaki segment
- Upozorenja kada segmenti ne odgovaraju

## Debug Endpoint

Dodat je debug endpoint `/api/chat/debug/sources` koji vraća:

- Raw LightRAG kontekst (vector i mix modovi)
- Izvučene metadata headere
- Validacione rezultate za segmente
- Parsirane izvore

Koristi se za debugging specifičnih upita:

```bash
POST /api/chat/debug/sources
{
  "query": "Var der en person som heter Marting og hvor jobber han?"
}
```

## Kako Testirati

1. **Koristite debug endpoint** da vidite šta LightRAG stvarno vraća:
   ```bash
   curl -X POST http://localhost:8000/api/chat/debug/sources \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"query": "Var der en person som heter Marting og hvor jobber han?"}'
   ```

2. **Proverite logove** - sada će biti mnogo detaljniji:
   ```bash
   tail -f backend/logs/app.log | grep -i "source\|header\|segment"
   ```

3. **Proverite database** - pronađite pravi segment:
   ```sql
   SELECT * FROM video_segments 
   WHERE text ILIKE '%Martin%' OR text ILIKE '%jobber%' 
   ORDER BY start_time;
   ```

## Primer Problema

Pitanje: "Var der en person som heter Marting og hvor jobber han?"

**Tačan segment u bazi:**
- Segment 54-55: "Mitt navn er Morten Thorvaldsen, jobber som arkivrådgiver i Sandefjord."
- Timestamp: ~235s

**Šta se dešavalo:**
- LightRAG je našao informaciju o Martinu/Morten kroz knowledge graph
- Vratio metadata headere iz semantički sličnih, ali pogrešnih segmenata
- Linkovi su pokazivali na pogrešne timestampove

**Kako je rešeno:**
- Vector-only mode vraća tačnije metadata headere
- Validacija proverava da segmenti stvarno sadrže relevantne informacije
- Fallback pretraga se koristi ako validacija ne prođe

## Buduća Poboljšanja

1. **Knowledge Graph Entity Tracking**: Prati koje segmente koristi knowledge graph entitet
2. **Semantic Similarity Check**: Koristi embedding sličnost između segmenta i odgovora
3. **Multiple Segment Aggregation**: Kombinuje više segmenata kada je informacija raštrkana
4. **User Feedback Loop**: Koristi korisnički feedback da poboljša matching
