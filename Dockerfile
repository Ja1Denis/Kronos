FROM python:3.12-slim

WORKDIR /app

# Instalacija sistemskih ovisnosti potrebnih za ChromaDB i ostale pakete
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Kopiraj requirements i instaliraj ovisnosti
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiraj cijeli kronos folder
COPY . .

# Postavi PYTHONPATH na root kronosa kako bi src.* importi radili
ENV PYTHONPATH=/app
ENV KRONOS_PORT=8765

# Izloži portove: 8765 za MCP, 8766 za Dashboard Logove
EXPOSE 8765
EXPOSE 8766

# Naredba za pokretanje u SSE modu
CMD ["python", "-m", "src.mcp_server", "--sse"]
