import json
import logging
import time
from confluent_kafka import Consumer, KafkaError, KafkaException
from app.core.telemetry import get_logger_with_context, set_propagated_context

logger = get_logger_with_context(__name__)

class KafkaConsumerService:
    def __init__(self, bootstrap_servers: str = 'kafka:9092', group_id: str = 'fastapi-consumer-group'):
        self.conf = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest',
            'session.timeout.ms': 6000,
            'heartbeat.interval.ms': 2000,
            'max.poll.interval.ms': 300000,
            'enable.auto.commit': False
        }
        self.consumer = None
        self.bootstrap_servers = bootstrap_servers
        self.running = False
        self._initialize_consumer()
    
    def _initialize_consumer(self):
        """Initialize consumer with retry logic"""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                self.consumer = Consumer(self.conf)
                logger.info("Kafka consumer initialized successfully", extra={"attributes": {
                    "bootstrap_servers": self.bootstrap_servers,
                    "attempt": attempt + 1
                }})
                return
            except Exception as e:
                logger.warning("Failed to initialize Kafka consumer", extra={"attributes": {
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "error": str(e),
                    "retry_delay": retry_delay
                }})
                if attempt == max_retries - 1:
                    raise
                time.sleep(retry_delay)
    
    def subscribe(self, topics: list):
        """Subscribe to topics"""
        try:
            self.consumer.subscribe(topics)
            logger.info("Subscribed to topics", extra={"attributes": {"topics": topics}})
        except Exception as e:
            logger.error("Failed to subscribe to topics", extra={"attributes": {
                "topics": topics,
                "error": str(e)
            }})
            raise
    
    def start_consuming(self):
        """Start consuming messages with proper error handling"""
        self.running = True
        logger.info("Starting Kafka consumer")
        
        try:
            while self.running:
                try:
                    msg = self.consumer.poll(1.0)
                    
                    if msg is None:
                        continue
                    
                    if msg.error():
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            logger.debug("Reached end of partition", extra={"attributes": {
                                "topic": msg.topic(),
                                "partition": msg.partition()
                            }})
                            continue
                        elif msg.error().code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                            logger.error("Topic or partition does not exist", extra={"attributes": {
                                "topic": msg.topic(),
                                "error": msg.error().str()
                            }})
                            time.sleep(5)
                            continue
                        else:
                            logger.error("Kafka consumer error", extra={"attributes": {
                                "error": msg.error().str(),
                                "code": msg.error().code()
                            }})
                            continue
                    
                    # Process the message
                    self._process_message(msg)
                    
                except KafkaException as e:
                    logger.error("Kafka exception occurred", extra={"attributes": {
                        "error": str(e)
                    }})
                    if not self.running:
                        break
                    time.sleep(5)
                except Exception as e:
                    logger.error("Unexpected error in consumer loop", extra={"attributes": {
                        "error": str(e)
                    }})
                    time.sleep(5)
                    
        except KeyboardInterrupt:
            logger.info("Consumer stopped by user")
        except Exception as e:
            logger.error("Consumer failed with error", extra={"attributes": {
                "error": str(e)
            }})
            raise
        finally:
            self.stop()
    
    def _process_message(self, msg):
        """Process a single message with context propagation"""
        try:
            # Parse message
            message_data = json.loads(msg.value().decode('utf-8'))
            
            # Extract context if available
            context = message_data.pop('_context', {})
            
            # Set the propagated context
            set_propagated_context(context)
            
            # Log message receipt
            logger.info("Message received from Kafka", extra={
                "attributes": {
                    "topic": msg.topic(),
                    "partition": msg.partition(),
                    "offset": msg.offset(),
                    "key": msg.key().decode('utf-8') if msg.key() else None,
                    "message_type": message_data.get('type', 'unknown')
                }
            })
            
            # Process based on message type
            if message_data.get('type') == 'pipeline_create':
                self._process_pipeline(message_data)
            elif message_data.get('type') == 'user_message':
                self._process_user_message(message_data)
            else:
                logger.warning("Unknown message type", extra={
                    "attributes": {"message_type": message_data.get('type', 'unknown')}
                })
                
            # Commit offset after successful processing
            self.consumer.commit(msg)
                
        except json.JSONDecodeError as e:
            logger.error("Failed to decode JSON message", extra={
                "attributes": {
                    "topic": msg.topic(),
                    "error": str(e)
                }
            })
        except Exception as e:
            logger.error("Failed to process message", extra={
                "attributes": {
                    "topic": msg.topic(),
                    "error": str(e)
                }
            })
    
    def _process_pipeline(self, message_data):
        """Process pipeline creation message"""
        from opentelemetry import trace
        tracer = trace.get_tracer(__name__)
        
        with tracer.start_as_current_span("pipeline.process.async"):
            pipeline_id = message_data['pipeline_id']
            steps = message_data['steps']
            
            logger.info("Processing async pipeline", extra={
                "attributes": {
                    "pipeline_id": pipeline_id,
                    "steps": steps,
                    "source": "kafka"
                }
            })
            
            # Simulate pipeline processing
            for step in range(1, steps + 1):
                import time
                processing_time = 0.3 + (step * 0.1)
                time.sleep(processing_time)
                
                logger.info("Async pipeline step completed", extra={
                    "attributes": {
                        "pipeline_id": pipeline_id,
                        "step": step,
                        "total_steps": steps,
                        "processing_time": processing_time
                    }
                })
            
            logger.info("Async pipeline completed", extra={
                "attributes": {"pipeline_id": pipeline_id}
            })
    
    def _process_user_message(self, message_data):
        """Process user message"""
        logger.info("Processing user message", extra={
            "attributes": {
                "content": message_data.get('content', ''),
                "sender": message_data.get('sender', 'unknown'),
                "message_length": len(message_data.get('content', ''))
            }
        })
    
    def stop(self):
        """Stop the consumer"""
        self.running = False
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer stopped")

# Singleton instance
kafka_consumer = KafkaConsumerService()