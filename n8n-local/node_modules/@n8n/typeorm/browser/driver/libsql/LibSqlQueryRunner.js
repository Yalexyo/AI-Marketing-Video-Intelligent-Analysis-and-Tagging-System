import { QueryRunnerAlreadyReleasedError } from "../../error/QueryRunnerAlreadyReleasedError";
import { QueryFailedError } from "../../error/QueryFailedError";
import { AbstractSqliteQueryRunner } from "../sqlite-abstract/AbstractSqliteQueryRunner";
import { Broadcaster } from "../../subscriber/Broadcaster";
import { ConnectionIsNotSetError } from "../../error/ConnectionIsNotSetError";
import { QueryResult } from "../../query-runner/QueryResult";
import { BroadcasterResult } from "../../subscriber/BroadcasterResult";
/**
 * Runs queries on a single libSQL database connection.
 */
export class LibSqlQueryRunner extends AbstractSqliteQueryRunner {
    // -------------------------------------------------------------------------
    // Constructor
    // -------------------------------------------------------------------------
    constructor(driver) {
        super();
        this.driver = driver;
        this.connection = driver.connection;
        this.broadcaster = new Broadcaster(this);
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
            throw new QueryRunnerAlreadyReleasedError();
        const connection = this.driver.connection;
        const options = connection.options;
        const maxQueryExecutionTime = options.maxQueryExecutionTime;
        const broadcasterResult = new BroadcasterResult();
        const broadcaster = this.broadcaster;
        broadcaster.broadcastBeforeQueryEvent(broadcasterResult, query, parameters);
        if (!connection.isInitialized) {
            throw new ConnectionIsNotSetError("libsql");
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
            const result = new QueryResult();
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
            throw new QueryFailedError(query, parameters, error);
        }
        finally {
            await broadcasterResult.wait();
        }
    }
}

//# sourceMappingURL=LibSqlQueryRunner.js.map
