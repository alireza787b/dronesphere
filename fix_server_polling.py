import re

# Fix server client to be more resilient during command execution
with open('dronesphere/server/client.py', 'r') as f:
    content = f.read()

# Make polling more resilient - don't treat timeouts as critical errors
old_request_code = '''            except Exception as e:
                logger.warning("agent_request_failed",
                             agent=f"{agent_host}:{agent_port}",
                             endpoint=endpoint,
                             attempt=attempt,
                             error=str(e))'''

new_request_code = '''            except Exception as e:
                # Only log warnings for actual failures, not timeouts during busy operations
                if "timeout" not in str(e).lower() and "connection" not in str(e).lower():
                    logger.warning("agent_request_failed",
                                 agent=f"{agent_host}:{agent_port}",
                                 endpoint=endpoint,
                                 attempt=attempt,
                                 error=str(e))
                else:
                    logger.debug("agent_request_timeout",
                               agent=f"{agent_host}:{agent_port}",
                               endpoint=endpoint,
                               attempt=attempt)'''

content = content.replace(old_request_code, new_request_code)

# Also reduce telemetry cache interval during operations
with open('dronesphere/server/coordinator/telemetry.py', 'r') as f:
    tel_content = f.read()

# Increase cache interval to reduce polling pressure
tel_content = tel_content.replace(
    'await asyncio.sleep(self.settings.telemetry_cache_interval)',
    'await asyncio.sleep(max(2.0, self.settings.telemetry_cache_interval))  # Min 2 second interval'
)

with open('dronesphere/server/client.py', 'w') as f:
    f.write(content)

with open('dronesphere/server/coordinator/telemetry.py', 'w') as f:
    f.write(tel_content)

print("✅ Fixed server polling resilience")
