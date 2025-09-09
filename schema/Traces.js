// schema/Traces.js
cube(`Traces`, {
  sql: `SELECT * FROM traces`,

  measures: {
    count: {
      type: `count`,
      drillMembers: [traceId, serviceName]
    },
    avgDuration: {
      sql: `duration`,
      type: `avg`
    }
  },

  dimensions: {
    traceId: {
      sql: `trace_id`,
      type: `string`,
      primaryKey: true
    },
    serviceName: {
      sql: `service_name`,
      type: `string`
    },
    timestamp: {
      sql: `timestamp`,
      type: `time`
    }
  }
});
