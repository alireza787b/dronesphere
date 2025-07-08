import re

# Read the current runner file
with open('dronesphere/agent/executor/runner.py', 'r') as f:
    content = f.read()

# Add failsafe imports
if 'from dronesphere.core.models import CommandResult' not in content:
    content = content.replace(
        'from dronesphere.core.models import (',
        'from dronesphere.core.models import (\n    CommandResult,'
    )

# Enhance the _execute_sequence method with robust error handling
old_execute = '''    async def _execute_sequence(self, envelope: CommandEnvelope) -> None:
        """Execute a command sequence."""
        for command in envelope.sequence:
            try:
                # Get command implementation
                registry = get_command_registry()
                
                # Create command instance with validated parameters
                command_impl = registry.create_command(command.name, command.params or {})
                
                # Execute command
                logger.info("executing_command", command=command.name, params=command.params)
                result = await command_impl.run(self.connection.backend, **command_impl.parameters)
                
                logger.info("command_completed", command=command.name, success=result.success)
                
                if not result.success:
                    logger.error("command_failed", command=command.name, error=result.error)
                    break
                    
            except Exception as e:
                logger.error("command_execution_error", command=command.name, error=str(e))
                break'''

new_execute = '''    async def _execute_sequence(self, envelope: CommandEnvelope) -> None:
        """Execute a command sequence with robust error handling and failsafe logic."""
        sequence_failed = False
        
        for cmd_index, command in enumerate(envelope.sequence):
            try:
                # Get command implementation and spec
                registry = get_command_registry()
                command_spec = registry.get_spec(command.name)
                
                # Extract criticality from metadata
                metadata = command_spec.spec.get("metadata", {})
                is_critical = metadata.get("critical", False)
                failsafe_action = metadata.get("failsafe", None)
                max_retries = metadata.get("max_retries", 0)
                timeout_behavior = metadata.get("timeout_behavior", "continue")
                
                logger.info("executing_command", 
                           command=command.name, 
                           params=command.params,
                           critical=is_critical,
                           cmd_index=cmd_index + 1,
                           total_commands=len(envelope.sequence))
                
                # Execute command with retry logic
                result = None
                last_error = None
                
                for attempt in range(max_retries + 1):
                    try:
                        # Create fresh command instance for each retry
                        command_impl = registry.create_command(command.name, command.params or {})
                        
                        if attempt > 0:
                            logger.warning("command_retry", 
                                         command=command.name, 
                                         attempt=attempt + 1,
                                         max_retries=max_retries + 1)
                        
                        result = await command_impl.run(self.connection.backend, **command_impl.parameters)
                        
                        if result.success:
                            break  # Success, exit retry loop
                        else:
                            last_error = result.error
                            
                    except Exception as e:
                        last_error = str(e)
                        logger.error("command_execution_exception", 
                                   command=command.name, 
                                   attempt=attempt + 1,
                                   error=str(e))
                
                # Handle command result
                if result and result.success:
                    logger.info("command_completed", 
                               command=command.name, 
                               success=True,
                               duration=getattr(result, 'duration', 0))
                else:
                    # Command failed after all retries
                    logger.error("command_failed", 
                               command=command.name, 
                               error=last_error,
                               critical=is_critical,
                               retries_exhausted=max_retries)
                    
                    if is_critical:
                        # Critical command failed - execute failsafe
                        logger.error("critical_command_failed", 
                                   command=command.name,
                                   triggering_failsafe=failsafe_action)
                        
                        if failsafe_action:
                            await self._execute_failsafe(failsafe_action)
                        
                        sequence_failed = True
                        break  # Stop sequence execution
                    else:
                        # Non-critical command failed - continue with next command
                        logger.warning("noncritical_command_failed_continuing", 
                                     command=command.name,
                                     error=last_error)
                        continue
                    
            except Exception as e:
                logger.error("command_execution_error", 
                           command=command.name, 
                           error=str(e))
                
                # For unexpected errors, treat as critical failure
                logger.error("unexpected_error_triggering_failsafe", error=str(e))
                await self._execute_failsafe("land")
                sequence_failed = True
                break
        
        # Log sequence completion
        if sequence_failed:
            logger.error("command_sequence_failed", 
                       envelope_id=getattr(envelope, 'id', 'unknown'))
        else:
            logger.info("command_sequence_completed", 
                       envelope_id=getattr(envelope, 'id', 'unknown'),
                       commands_executed=len(envelope.sequence))
    
    async def _execute_failsafe(self, failsafe_action: str) -> None:
        """Execute failsafe action."""
        try:
            logger.warning("executing_failsafe", action=failsafe_action)
            
            if failsafe_action == "land":
                # Emergency land
                registry = get_command_registry()
                land_command = registry.create_command("land", {})
                result = await land_command.run(self.connection.backend, **land_command.parameters)
                
                if result.success:
                    logger.info("failsafe_land_completed")
                else:
                    logger.error("failsafe_land_failed", error=result.error)
                    
            elif failsafe_action == "rtl":
                # Return to launch
                registry = get_command_registry()
                rtl_command = registry.create_command("rtl", {})
                result = await rtl_command.run(self.connection.backend, **rtl_command.parameters)
                
                if result.success:
                    logger.info("failsafe_rtl_completed")
                else:
                    logger.error("failsafe_rtl_failed", error=result.error)
                    
            elif failsafe_action == "emergency_stop":
                # Emergency stop
                await self.connection.emergency_stop()
                logger.info("failsafe_emergency_stop_completed")
                
        except Exception as e:
            logger.error("failsafe_execution_failed", 
                       action=failsafe_action, 
                       error=str(e))'''

# Replace the method
content = re.sub(
    r'    async def _execute_sequence\(self, envelope: CommandEnvelope\) -> None:.*?(?=\n    def|\n    async def|\nclass|\Z)',
    new_execute,
    content,
    flags=re.DOTALL
)

# Write the enhanced file
with open('dronesphere/agent/executor/runner.py', 'w') as f:
    f.write(content)

print("✅ Enhanced command runner with robust failsafe logic")
