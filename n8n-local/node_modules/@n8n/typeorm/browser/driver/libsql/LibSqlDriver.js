import { AbstractSqliteDriver } from "../sqlite-abstract/AbstractSqliteDriver";
import { LibSqlQueryRunner } from "./LibSqlQueryRunner";
import { PlatformTools } from "../../platform/PlatformTools";
import { DriverPackageNotInstalledError } from "../../error/DriverPackageNotInstalledError";
export class LibSqlDriver extends AbstractSqliteDriver {
    constructor(connection) {
        super(connection);
        this.database = this.options.database;
        try {
            this.sqlite = PlatformTools.load("libsql");
        }
        catch (e) {
            throw new DriverPackageNotInstalledError("SQLite", "sqlite3");
        }
    }
    /**
     * Closes connection with database.
     */
    async disconnect() {
        return new Promise((ok, fail) => {
            try {
                this.queryRunner = undefined;
                this.databaseConnection?.close();
                this.databaseConnection = undefined;
                ok();
            }
            catch (error) {
                fail(error);
            }
        });
    }
    /**
     * Creates a query runner used to execute database queries.
     */
    createQueryRunner() {
        if (!this.queryRunner)
            this.queryRunner = new LibSqlQueryRunner(this);
        return this.queryRunner;
    }
    createGeneratedMap(metadata, insertResult, entityIndex, entityNum) {
        if (typeof insertResult === "bigint")
            insertResult = Number(insertResult);
        return super.createGeneratedMap(metadata, insertResult, entityIndex, entityNum);
    }
    normalizeType(column) {
        return column.type === Buffer
            ? "blob"
            : super.normalizeType(column);
    }
    // -------------------------------------------------------------------------
    // Protected Methods
    // -------------------------------------------------------------------------
    /**
     * Creates connection with the database.
     */
    async createDatabaseConnection() {
        const client = this.sqlite.createClient({
            url: `file:${this.database}`,
            intMode: "number",
        });
        if (this.options.enableWAL) {
            await client.execute("PRAGMA journal_mode = WAL");
        }
        /*
        // we need to enable foreign keys in libsql to make sure all foreign key related features working properly.
            this also makes onDelete work with libsql.
        */
        await client.execute("PRAGMA foreign_keys = ON");
        return client;
    }
}

//# sourceMappingURL=LibSqlDriver.js.map
