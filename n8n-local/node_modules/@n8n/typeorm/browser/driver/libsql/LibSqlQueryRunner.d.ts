import { AbstractSqliteQueryRunner } from "../sqlite-abstract/AbstractSqliteQueryRunner";
import type { LibSqlDriver } from "./LibSqlDriver";
/**
 * Runs queries on a single libSQL database connection.
 */
export declare class LibSqlQueryRunner extends AbstractSqliteQueryRunner {
    /**
     * Database driver used by connection.
     */
    driver: LibSqlDriver;
    constructor(driver: LibSqlDriver);
    /**
     * Called before migrations are run.
     */
    beforeMigration(): Promise<void>;
    /**
     * Called after migrations are run.
     */
    afterMigration(): Promise<void>;
    /**
     * Executes a given SQL query.
     */
    query(query: string, parameters?: any[], useStructuredResult?: boolean): Promise<any>;
}
