"use strict";
Object.defineProperty(exports, "__esModule", {
    value: true
});
Object.defineProperty(exports, "default", {
    enumerable: true,
    get: function() {
        return isNetworkError;
    }
});
var objectToString = Object.prototype.toString;
var isError = function(value) {
    return objectToString.call(value) === "[object Error]";
};
var errorMessages = new Set([
    "network error",
    "Failed to fetch",
    "NetworkError when attempting to fetch resource.",
    "The Internet connection appears to be offline.",
    "Load failed",
    "Network request failed",
    "fetch failed"
]);
function isNetworkError(error) {
    var isValid = error && isError(error) && error.name === "TypeError" && typeof error.message === "string";
    if (!isValid) {
        return false;
    }
    // We do an extra check for Safari 17+ as it has a very generic error message.
    // Network errors in Safari have no stack.
    if (error.message === "Load failed") {
        return error.stack === undefined;
    }
    return errorMessages.has(error.message);
}
