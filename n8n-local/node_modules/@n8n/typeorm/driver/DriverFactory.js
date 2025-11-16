"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.DriverFactory = void 0;
const MissingDriverError_1 = require("../error/MissingDriverError");
const getDriver = async (type) => {
    switch (type) {
        case "mysql":
        case "mariadb":
            return (await Promise.resolve().then(() => __importStar(require("./mysql/MysqlDriver")))).MysqlDriver;
        case "postgres":
            return (await Promise.resolve().then(() => __importStar(require("./postgres/PostgresDriver")))).PostgresDriver;
        case "cockroachdb":
            return (await Promise.resolve().then(() => __importStar(require("./cockroachdb/CockroachDriver"))))
                .CockroachDriver;
        case "sap":
            return (await Promise.resolve().then(() => __importStar(require("./sap/SapDriver")))).SapDriver;
        case "sqlite":
            return (await Promise.resolve().then(() => __importStar(require("./sqlite/SqliteDriver")))).SqliteDriver;
        case "sqlite-pooled":
            return (await Promise.resolve().then(() => __importStar(require("./sqlite-pooled/SqliteReadWriteDriver"))))
                .SqliteReadWriteDriver;
        case "better-sqlite3":
            return (await Promise.resolve().then(() => __importStar(require("./better-sqlite3/BetterSqlite3Driver"))))
                .BetterSqlite3Driver;
        case "cordova":
            return (await Promise.resolve().then(() => __importStar(require("./cordova/CordovaDriver")))).CordovaDriver;
        case "nativescript":
            return (await Promise.resolve().then(() => __importStar(require("./nativescript/NativescriptDriver"))))
                .NativescriptDriver;
        case "react-native":
            return (await Promise.resolve().then(() => __importStar(require("./react-native/ReactNativeDriver"))))
                .ReactNativeDriver;
        case "sqljs":
            return (await Promise.resolve().then(() => __importStar(require("./sqljs/SqljsDriver")))).SqljsDriver;
        case "oracle":
            return (await Promise.resolve().then(() => __importStar(require("./oracle/OracleDriver")))).OracleDriver;
        case "mssql":
            return (await Promise.resolve().then(() => __importStar(require("./sqlserver/SqlServerDriver")))).SqlServerDriver;
        case "mongodb":
            return (await Promise.resolve().then(() => __importStar(require("./mongodb/MongoDriver")))).MongoDriver;
        case "expo":
            return (await Promise.resolve().then(() => __importStar(require("./expo/ExpoDriver")))).ExpoDriver;
        case "aurora-mysql":
            return (await Promise.resolve().then(() => __importStar(require("./aurora-mysql/AuroraMysqlDriver"))))
                .AuroraMysqlDriver;
        case "aurora-postgres":
            return (await Promise.resolve().then(() => __importStar(require("./aurora-postgres/AuroraPostgresDriver"))))
                .AuroraPostgresDriver;
        case "capacitor":
            return (await Promise.resolve().then(() => __importStar(require("./capacitor/CapacitorDriver")))).CapacitorDriver;
        case "spanner":
            return (await Promise.resolve().then(() => __importStar(require("./spanner/SpannerDriver")))).SpannerDriver;
        case "libsql":
            return (await Promise.resolve().then(() => __importStar(require("./libsql/LibSqlDriver")))).LibSqlDriver;
        default:
            throw new MissingDriverError_1.MissingDriverError(type, [
                "aurora-mysql",
                "aurora-postgres",
                "better-sqlite3",
                "capacitor",
                "cockroachdb",
                "cordova",
                "expo",
                "mariadb",
                "mongodb",
                "mssql",
                "mysql",
                "nativescript",
                "oracle",
                "postgres",
                "react-native",
                "sap",
                "sqlite",
                "sqlite-pooled",
                "sqljs",
                "spanner",
                "libsql",
            ]);
    }
};
/**
 * Helps to create drivers.
 */
class DriverFactory {
    /**
     * Creates a new driver depend on a given connection's driver type.
     */
    static async create(connection) {
        const { type } = connection.options;
        return new (await getDriver(type))(connection);
    }
}
exports.DriverFactory = DriverFactory;

//# sourceMappingURL=DriverFactory.js.map
