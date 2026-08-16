from database import create_collection_snapshot


snapshot = create_collection_snapshot(
    usd_brl=5.40,
)


print()
print(
    "===== RESULTADO ====="
)

print(
    snapshot
)