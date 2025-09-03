#!/usr/bin/env python3
import logging
from app.infrastructure.kafka_consumer import kafka_consumer
from app.core.telemetry import get_logger_with_context

logger = get_logger_with_context(__name__)

if __name__ == "__main__":
    logger.info("Starting Kafka consumer service")
    
    # Subscribe to topics
    kafka_consumer.subscribe(['pipelines', 'test-topic'])
    
    # Start consuming
    try:
        kafka_consumer.start_consuming()
    except Exception as e:
        logger.error("Consumer failed", extra={"attributes": {"error": str(e)}})
        raise