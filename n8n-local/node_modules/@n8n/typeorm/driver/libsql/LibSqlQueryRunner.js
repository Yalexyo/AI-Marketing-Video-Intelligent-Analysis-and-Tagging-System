"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.LibSqlQueryRunner = void 0;
const QueryRunnerAlreadyReleasedError_1 = require("../../error/QueryRunnerAlreadyReleasedError");
const QueryFailedError_1 = require("../../error/QueryFailedError");
const AbstractSqliteQueryRunner_1 = require("../sqlite-abstract/AbstractSqliteQueryRunner");
const Broadcaster_1 = require("../../subscriber/Broadcaster");
const ConnectionIsNotSetError_1 = require("../../error/ConnectionIsNotSetError");
const QueryResult_1 = require("../../query-runner/QueryResult");
const BroadcasterResult_1 = require("../../subscriber/BroadcasterResult");
/**
 * Runs queries on a single libSQL database connection.
 */
class LibSqlQueryRunner extends AbstractSqliteQueryRunner_1.AbstractSqliteQueryRunner {
    // -------------------------------------------------------------------------
    // Constructor
    // -------------------------------------------------------------------------
    constructor(driver) {
        super();
        this.driver = driver;
        this.connection = driver.connection;
        this.broadcaster = new Broadcaster_1.Broadcaster(this);
    }
    /**
     * Called before migrations are run.
     */
    async beforeMigration() {
        await this.query(`PRAGMA foreign_keys = OFF`);
    }
    /**
     * Called after migrations are run.
     */
    async afterMigration() {
        await this.query(`PRAGMA foreign_keys = ON`);
    }
    /**
     * Executes a given SQL query.
     */
    async query(query, parameters, useStructuredResult = false) {
        if (this.isReleased)
            throw new QueryRunnerAlreadyReleasedError_1.QueryRunnerAlreadyReleasedError();
        const connection = this.driver.connection;
        const options = connection.options;
        const maxQueryExecutionTime = options.maxQueryExecutionTime;
        const broadcasterResult = new BroadcasterResult_1.BroadcasterResult();
        const broadcaster = this.broadcaster;
        broadcaster.broadcastBeforeQueryEvent(broadcasterResult, query, parameters);
        if (!connection.isInitialized) {
            throw new ConnectionIsNotSetError_1.ConnectionIsNotSetError("libsql");
        }
        try {
            const databaseConnection = (await this.connect());
            this.driver.connection.logger.logQuery(query, parameters, this);
            const queryStartTime = Date.now();
            const args = (parameters ?? []).map((p) => p === undefined ? null : p);
            const resultSet = await databaseConnection.execute({ sql: query, args });
            // log slow queries if maxQueryExecution time is set
            const queryEndTime = Date.now();
            const queryExecutionTime = queryEndTime - queryStartTime;
            if (maxQueryExecutionTime) {
                if (queryExecutionTime > maxQueryExecutionTime)
                    connection.logger.logQuerySlow(queryExecutionTime, query, parameters, this);
            }
            const result = new QueryResult_1.QueryResult();
            if (query.startsWith("INSERT ")) {
                result.raw = resultSet.lastInsertRowid;
            }
            else {
                result.raw = resultSet.rows;
            }
            broadcaster.broadcastAfterQueryEvent(broadcasterResult, query, parameters, true, queryExecutionTime, result.raw, undefined);
            if (Array.isArray(resultSet.rows)) {
                result.records = resultSet.rows;
            }
            result.affected = resultSet.rowsAffected;
            return useStructuredResult ? result : result.raw;
        }
        catch (error) {
            connection.logger.logQueryError(error, query, parameters, this);
            broadcaster.broadcastAfterQueryEvent(broadcasterResult, query, parameters, false, undefined, undefined, error);
            throw new QueryFailedError_1.QueryFailedError(query, parameters, error);
        }
        finally {
            await broadcasterResult.wait();
        }
    }
}
exports.LibSqlQueryRunner = LibSqlQueryRunner;

//# sourceMappingURL=LibSqlQueryRunner.js.map
