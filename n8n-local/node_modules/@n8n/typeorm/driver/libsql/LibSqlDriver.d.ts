import type { createClient } from "@libsql/client";
import { AbstractSqliteDriver } from "../sqlite-abstract/AbstractSqliteDriver";
import type { LibSqlConnectionOptions } from "./LibSqlConnectionOptions";
import type { QueryRunner } from "../../query-runner/QueryRunner";
import type { DataSource } from "../../data-source/DataSource";
import type { EntityMetadata } from "../../metadata/EntityMetadata";
import type { ColumnType } from "../types/ColumnTypes";
export declare class LibSqlDriver extends AbstractSqliteDriver {
    sqlite: {
        createClient: typeof createClient;
    };
    options: LibSqlConnectionOptions;
    constructor(connection: DataSource);
    /**
     * Closes connection with database.
     */
    disconnect(): Promise<void>;
    /**
     * Creates a query runner used to execute database queries.
     */
    createQueryRunner(): QueryRunner;
    createGeneratedMap(metadata: EntityMetadata, insertResult: any, entityIndex: number, entityNum: number): any;
    normalizeType(column: {
        type?: ColumnType;
        length?: number | string;
        precision?: number | null;
        scale?: number;
    }): string;
    /**
     * Creates connection with the database.
     */
    protected createDatabaseConnection(): Promise<import("@libsql/client/.").Client>;
}
