# Deployment Guide

## Fly.io Deployment

### Initial Setup

1. **Create the persistent volume:**
   ```bash
   fly volumes create bot_data --size 1 --region iad
   ```

2. **Deploy the application:**
   ```bash
   fly deploy
   ```

### Data Persistence

The bot uses a persistent volume mounted at `/app/data` to store:
- `messages.db` - SQLite database with indexed messages and embeddings
- Database journal files (WAL, etc.)

The volume is configured in `fly.toml`:
```toml
[mounts]
  source = "bot_data"
  destination = "/app/data"
```

### Backfilling Historical Messages

After deployment, you can backfill historical messages using the `/backfill_messages` command:

```
/backfill_messages 1000
```

This will index up to 1000 messages per channel. Adjust the limit based on your needs (1-10000).

**Note:** Backfilling can take a while and will consume API credits for embedding generation. Start with a smaller limit to test.

### Monitoring

- View logs: `fly logs`
- Check volume usage: `fly volumes list`
- SSH into the instance: `fly ssh console`

### Troubleshooting

**Volume not mounting:**
- Ensure the volume exists: `fly volumes list`
- Check volume is in the same region as your app
- Verify `fly.toml` has the correct mount configuration

**Database errors:**
- Check volume has space: `fly volumes list`
- Verify permissions on the data directory
- Check logs for specific errors: `fly logs`

## VPS Deployment

For VPS deployments, ensure:
1. The `data/` directory exists and is writable
2. Database files persist across restarts (not in `/tmp`)
3. Consider using systemd or similar for process management
4. Set up log rotation for the application logs

