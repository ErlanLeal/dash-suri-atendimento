# Control Tower · Customer Service

SLA dashboard for the customer service queue. It reads daily snapshots from PostgreSQL and shows where the queue is healthy, where it is on alert and where it is late.

## Views

**Operational (daily)**
- Queue size for the selected snapshot, with the change from the previous day
- Share of items OK (under 4 days), on alert (4 days) and late (over 4 days)
- Top 10 bottlenecks by health insurer, ranked by average delay
- Exceptions table with every item on alert or late

**Planning (capacity)**
- Queue volume over 7, 15, 30 or 60 days
- Average delay trend over the same window

## Stack

Python · Streamlit · Pandas · Plotly · SQLAlchemy · PostgreSQL

## Running locally

```bash
pip install -r requirements.txt
streamlit run app_atendimento.py
```

The app connects through `st.connection("postgresql")`, so it needs a `.streamlit/secrets.toml` with the database credentials:

```toml
[connections.postgresql]
dialect = "postgresql"
host = "..."
port = "5432"
database = "..."
username = "..."
password = "..."
```

It expects a `sla_atendimento` table with `id`, `id_empresa`, `data_snapshot`, `dias_atraso`, `nome_empresa`, `operadora`, `corretora` and `fila_atual`.
