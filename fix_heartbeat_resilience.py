import re

with open('dronesphere/agent/heartbeat.py', 'r') as f:
    content = f.read()

# Make heartbeat more resilient to temporary failures
old_heartbeat = '''        except Exception as e:
            self.consecutive_failures += 1
            logger.warning("heartbeat_error", 
                         consecutive_failures=self.consecutive_failures,
                         error=str(e))'''

new_heartbeat = '''        except Exception as e:
            self.consecutive_failures += 1
            # Only log warnings after multiple failures to reduce noise
            if self.consecutive_failures <= 2:
                logger.debug("heartbeat_retry", 
                           consecutive_failures=self.consecutive_failures,
                           error=str(e))
            else:
                logger.warning("heartbeat_error", 
                             consecutive_failures=self.consecutive_failures,
                             error=str(e))'''

content = content.replace(old_heartbeat, new_heartbeat)

with open('dronesphere/agent/heartbeat.py', 'w') as f:
    f.write(content)

print("✅ Enhanced heartbeat resilience")
