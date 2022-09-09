/******/ (function(modules) { // webpackBootstrap
/******/ 	function hotDisposeChunk(chunkId) {
/******/ 		delete installedChunks[chunkId];
/******/ 	}
/******/ 	var parentHotUpdateCallback = window["webpackHotUpdate"];
/******/ 	window["webpackHotUpdate"] = // eslint-disable-next-line no-unused-vars
/******/ 	function webpackHotUpdateCallback(chunkId, moreModules) {
/******/ 		hotAddUpdateChunk(chunkId, moreModules);
/******/ 		if (parentHotUpdateCallback) parentHotUpdateCallback(chunkId, moreModules);
/******/ 	} ;
/******/
/******/ 	// eslint-disable-next-line no-unused-vars
/******/ 	function hotDownloadUpdateChunk(chunkId) {
/******/ 		var script = document.createElement("script");
/******/ 		script.charset = "utf-8";
/******/ 		script.src = __webpack_require__.p + "" + chunkId + "." + hotCurrentHash + ".hot-update.js";
/******/ 		if (null) script.crossOrigin = null;
/******/ 		document.head.appendChild(script);
/******/ 	}
/******/
/******/ 	// eslint-disable-next-line no-unused-vars
/******/ 	function hotDownloadManifest(requestTimeout) {
/******/ 		requestTimeout = requestTimeout || 10000;
/******/ 		return new Promise(function(resolve, reject) {
/******/ 			if (typeof XMLHttpRequest === "undefined") {
/******/ 				return reject(new Error("No browser support"));
/******/ 			}
/******/ 			try {
/******/ 				var request = new XMLHttpRequest();
/******/ 				var requestPath = __webpack_require__.p + "" + hotCurrentHash + ".hot-update.json";
/******/ 				request.open("GET", requestPath, true);
/******/ 				request.timeout = requestTimeout;
/******/ 				request.send(null);
/******/ 			} catch (err) {
/******/ 				return reject(err);
/******/ 			}
/******/ 			request.onreadystatechange = function() {
/******/ 				if (request.readyState !== 4) return;
/******/ 				if (request.status === 0) {
/******/ 					// timeout
/******/ 					reject(
/******/ 						new Error("Manifest request to " + requestPath + " timed out.")
/******/ 					);
/******/ 				} else if (request.status === 404) {
/******/ 					// no update available
/******/ 					resolve();
/******/ 				} else if (request.status !== 200 && request.status !== 304) {
/******/ 					// other failure
/******/ 					reject(new Error("Manifest request to " + requestPath + " failed."));
/******/ 				} else {
/******/ 					// success
/******/ 					try {
/******/ 						var update = JSON.parse(request.responseText);
/******/ 					} catch (e) {
/******/ 						reject(e);
/******/ 						return;
/******/ 					}
/******/ 					resolve(update);
/******/ 				}
/******/ 			};
/******/ 		});
/******/ 	}
/******/
/******/ 	var hotApplyOnUpdate = true;
/******/ 	// eslint-disable-next-line no-unused-vars
/******/ 	var hotCurrentHash = "70fa1f7d60435acf4f1d";
/******/ 	var hotRequestTimeout = 10000;
/******/ 	var hotCurrentModuleData = {};
/******/ 	var hotCurrentChildModule;
/******/ 	// eslint-disable-next-line no-unused-vars
/******/ 	var hotCurrentParents = [];
/******/ 	// eslint-disable-next-line no-unused-vars
/******/ 	var hotCurrentParentsTemp = [];
/******/
/******/ 	// eslint-disable-next-line no-unused-vars
/******/ 	function hotCreateRequire(moduleId) {
/******/ 		var me = installedModules[moduleId];
/******/ 		if (!me) return __webpack_require__;
/******/ 		var fn = function(request) {
/******/ 			if (me.hot.active) {
/******/ 				if (installedModules[request]) {
/******/ 					if (installedModules[request].parents.indexOf(moduleId) === -1) {
/******/ 						installedModules[request].parents.push(moduleId);
/******/ 					}
/******/ 				} else {
/******/ 					hotCurrentParents = [moduleId];
/******/ 					hotCurrentChildModule = request;
/******/ 				}
/******/ 				if (me.children.indexOf(request) === -1) {
/******/ 					me.children.push(request);
/******/ 				}
/******/ 			} else {
/******/ 				console.warn(
/******/ 					"[HMR] unexpected require(" +
/******/ 						request +
/******/ 						") from disposed module " +
/******/ 						moduleId
/******/ 				);
/******/ 				hotCurrentParents = [];
/******/ 			}
/******/ 			return __webpack_require__(request);
/******/ 		};
/******/ 		var ObjectFactory = function ObjectFactory(name) {
/******/ 			return {
/******/ 				configurable: true,
/******/ 				enumerable: true,
/******/ 				get: function() {
/******/ 					return __webpack_require__[name];
/******/ 				},
/******/ 				set: function(value) {
/******/ 					__webpack_require__[name] = value;
/******/ 				}
/******/ 			};
/******/ 		};
/******/ 		for (var name in __webpack_require__) {
/******/ 			if (
/******/ 				Object.prototype.hasOwnProperty.call(__webpack_require__, name) &&
/******/ 				name !== "e" &&
/******/ 				name !== "t"
/******/ 			) {
/******/ 				Object.defineProperty(fn, name, ObjectFactory(name));
/******/ 			}
/******/ 		}
/******/ 		fn.e = function(chunkId) {
/******/ 			if (hotStatus === "ready") hotSetStatus("prepare");
/******/ 			hotChunksLoading++;
/******/ 			return __webpack_require__.e(chunkId).then(finishChunkLoading, function(err) {
/******/ 				finishChunkLoading();
/******/ 				throw err;
/******/ 			});
/******/
/******/ 			function finishChunkLoading() {
/******/ 				hotChunksLoading--;
/******/ 				if (hotStatus === "prepare") {
/******/ 					if (!hotWaitingFilesMap[chunkId]) {
/******/ 						hotEnsureUpdateChunk(chunkId);
/******/ 					}
/******/ 					if (hotChunksLoading === 0 && hotWaitingFiles === 0) {
/******/ 						hotUpdateDownloaded();
/******/ 					}
/******/ 				}
/******/ 			}
/******/ 		};
/******/ 		fn.t = function(value, mode) {
/******/ 			if (mode & 1) value = fn(value);
/******/ 			return __webpack_require__.t(value, mode & ~1);
/******/ 		};
/******/ 		return fn;
/******/ 	}
/******/
/******/ 	// eslint-disable-next-line no-unused-vars
/******/ 	function hotCreateModule(moduleId) {
/******/ 		var hot = {
/******/ 			// private stuff
/******/ 			_acceptedDependencies: {},
/******/ 			_declinedDependencies: {},
/******/ 			_selfAccepted: false,
/******/ 			_selfDeclined: false,
/******/ 			_selfInvalidated: false,
/******/ 			_disposeHandlers: [],
/******/ 			_main: hotCurrentChildModule !== moduleId,
/******/
/******/ 			// Module API
/******/ 			active: true,
/******/ 			accept: function(dep, callback) {
/******/ 				if (dep === undefined) hot._selfAccepted = true;
/******/ 				else if (typeof dep === "function") hot._selfAccepted = dep;
/******/ 				else if (typeof dep === "object")
/******/ 					for (var i = 0; i < dep.length; i++)
/******/ 						hot._acceptedDependencies[dep[i]] = callback || function() {};
/******/ 				else hot._acceptedDependencies[dep] = callback || function() {};
/******/ 			},
/******/ 			decline: function(dep) {
/******/ 				if (dep === undefined) hot._selfDeclined = true;
/******/ 				else if (typeof dep === "object")
/******/ 					for (var i = 0; i < dep.length; i++)
/******/ 						hot._declinedDependencies[dep[i]] = true;
/******/ 				else hot._declinedDependencies[dep] = true;
/******/ 			},
/******/ 			dispose: function(callback) {
/******/ 				hot._disposeHandlers.push(callback);
/******/ 			},
/******/ 			addDisposeHandler: function(callback) {
/******/ 				hot._disposeHandlers.push(callback);
/******/ 			},
/******/ 			removeDisposeHandler: function(callback) {
/******/ 				var idx = hot._disposeHandlers.indexOf(callback);
/******/ 				if (idx >= 0) hot._disposeHandlers.splice(idx, 1);
/******/ 			},
/******/ 			invalidate: function() {
/******/ 				this._selfInvalidated = true;
/******/ 				switch (hotStatus) {
/******/ 					case "idle":
/******/ 						hotUpdate = {};
/******/ 						hotUpdate[moduleId] = modules[moduleId];
/******/ 						hotSetStatus("ready");
/******/ 						break;
/******/ 					case "ready":
/******/ 						hotApplyInvalidatedModule(moduleId);
/******/ 						break;
/******/ 					case "prepare":
/******/ 					case "check":
/******/ 					case "dispose":
/******/ 					case "apply":
/******/ 						(hotQueuedInvalidatedModules =
/******/ 							hotQueuedInvalidatedModules || []).push(moduleId);
/******/ 						break;
/******/ 					default:
/******/ 						// ignore requests in error states
/******/ 						break;
/******/ 				}
/******/ 			},
/******/
/******/ 			// Management API
/******/ 			check: hotCheck,
/******/ 			apply: hotApply,
/******/ 			status: function(l) {
/******/ 				if (!l) return hotStatus;
/******/ 				hotStatusHandlers.push(l);
/******/ 			},
/******/ 			addStatusHandler: function(l) {
/******/ 				hotStatusHandlers.push(l);
/******/ 			},
/******/ 			removeStatusHandler: function(l) {
/******/ 				var idx = hotStatusHandlers.indexOf(l);
/******/ 				if (idx >= 0) hotStatusHandlers.splice(idx, 1);
/******/ 			},
/******/
/******/ 			//inherit from previous dispose call
/******/ 			data: hotCurrentModuleData[moduleId]
/******/ 		};
/******/ 		hotCurrentChildModule = undefined;
/******/ 		return hot;
/******/ 	}
/******/
/******/ 	var hotStatusHandlers = [];
/******/ 	var hotStatus = "idle";
/******/
/******/ 	function hotSetStatus(newStatus) {
/******/ 		hotStatus = newStatus;
/******/ 		for (var i = 0; i < hotStatusHandlers.length; i++)
/******/ 			hotStatusHandlers[i].call(null, newStatus);
/******/ 	}
/******/
/******/ 	// while downloading
/******/ 	var hotWaitingFiles = 0;
/******/ 	var hotChunksLoading = 0;
/******/ 	var hotWaitingFilesMap = {};
/******/ 	var hotRequestedFilesMap = {};
/******/ 	var hotAvailableFilesMap = {};
/******/ 	var hotDeferred;
/******/
/******/ 	// The update info
/******/ 	var hotUpdate, hotUpdateNewHash, hotQueuedInvalidatedModules;
/******/
/******/ 	function toModuleId(id) {
/******/ 		var isNumber = +id + "" === id;
/******/ 		return isNumber ? +id : id;
/******/ 	}
/******/
/******/ 	function hotCheck(apply) {
/******/ 		if (hotStatus !== "idle") {
/******/ 			throw new Error("check() is only allowed in idle status");
/******/ 		}
/******/ 		hotApplyOnUpdate = apply;
/******/ 		hotSetStatus("check");
/******/ 		return hotDownloadManifest(hotRequestTimeout).then(function(update) {
/******/ 			if (!update) {
/******/ 				hotSetStatus(hotApplyInvalidatedModules() ? "ready" : "idle");
/******/ 				return null;
/******/ 			}
/******/ 			hotRequestedFilesMap = {};
/******/ 			hotWaitingFilesMap = {};
/******/ 			hotAvailableFilesMap = update.c;
/******/ 			hotUpdateNewHash = update.h;
/******/
/******/ 			hotSetStatus("prepare");
/******/ 			var promise = new Promise(function(resolve, reject) {
/******/ 				hotDeferred = {
/******/ 					resolve: resolve,
/******/ 					reject: reject
/******/ 				};
/******/ 			});
/******/ 			hotUpdate = {};
/******/ 			var chunkId = "openassessment-editor-tinymce";
/******/ 			// eslint-disable-next-line no-lone-blocks
/******/ 			{
/******/ 				hotEnsureUpdateChunk(chunkId);
/******/ 			}
/******/ 			if (
/******/ 				hotStatus === "prepare" &&
/******/ 				hotChunksLoading === 0 &&
/******/ 				hotWaitingFiles === 0
/******/ 			) {
/******/ 				hotUpdateDownloaded();
/******/ 			}
/******/ 			return promise;
/******/ 		});
/******/ 	}
/******/
/******/ 	// eslint-disable-next-line no-unused-vars
/******/ 	function hotAddUpdateChunk(chunkId, moreModules) {
/******/ 		if (!hotAvailableFilesMap[chunkId] || !hotRequestedFilesMap[chunkId])
/******/ 			return;
/******/ 		hotRequestedFilesMap[chunkId] = false;
/******/ 		for (var moduleId in moreModules) {
/******/ 			if (Object.prototype.hasOwnProperty.call(moreModules, moduleId)) {
/******/ 				hotUpdate[moduleId] = moreModules[moduleId];
/******/ 			}
/******/ 		}
/******/ 		if (--hotWaitingFiles === 0 && hotChunksLoading === 0) {
/******/ 			hotUpdateDownloaded();
/******/ 		}
/******/ 	}
/******/
/******/ 	function hotEnsureUpdateChunk(chunkId) {
/******/ 		if (!hotAvailableFilesMap[chunkId]) {
/******/ 			hotWaitingFilesMap[chunkId] = true;
/******/ 		} else {
/******/ 			hotRequestedFilesMap[chunkId] = true;
/******/ 			hotWaitingFiles++;
/******/ 			hotDownloadUpdateChunk(chunkId);
/******/ 		}
/******/ 	}
/******/
/******/ 	function hotUpdateDownloaded() {
/******/ 		hotSetStatus("ready");
/******/ 		var deferred = hotDeferred;
/******/ 		hotDeferred = null;
/******/ 		if (!deferred) return;
/******/ 		if (hotApplyOnUpdate) {
/******/ 			// Wrap deferred object in Promise to mark it as a well-handled Promise to
/******/ 			// avoid triggering uncaught exception warning in Chrome.
/******/ 			// See https://bugs.chromium.org/p/chromium/issues/detail?id=465666
/******/ 			Promise.resolve()
/******/ 				.then(function() {
/******/ 					return hotApply(hotApplyOnUpdate);
/******/ 				})
/******/ 				.then(
/******/ 					function(result) {
/******/ 						deferred.resolve(result);
/******/ 					},
/******/ 					function(err) {
/******/ 						deferred.reject(err);
/******/ 					}
/******/ 				);
/******/ 		} else {
/******/ 			var outdatedModules = [];
/******/ 			for (var id in hotUpdate) {
/******/ 				if (Object.prototype.hasOwnProperty.call(hotUpdate, id)) {
/******/ 					outdatedModules.push(toModuleId(id));
/******/ 				}
/******/ 			}
/******/ 			deferred.resolve(outdatedModules);
/******/ 		}
/******/ 	}
/******/
/******/ 	function hotApply(options) {
/******/ 		if (hotStatus !== "ready")
/******/ 			throw new Error("apply() is only allowed in ready status");
/******/ 		options = options || {};
/******/ 		return hotApplyInternal(options);
/******/ 	}
/******/
/******/ 	function hotApplyInternal(options) {
/******/ 		hotApplyInvalidatedModules();
/******/
/******/ 		var cb;
/******/ 		var i;
/******/ 		var j;
/******/ 		var module;
/******/ 		var moduleId;
/******/
/******/ 		function getAffectedStuff(updateModuleId) {
/******/ 			var outdatedModules = [updateModuleId];
/******/ 			var outdatedDependencies = {};
/******/
/******/ 			var queue = outdatedModules.map(function(id) {
/******/ 				return {
/******/ 					chain: [id],
/******/ 					id: id
/******/ 				};
/******/ 			});
/******/ 			while (queue.length > 0) {
/******/ 				var queueItem = queue.pop();
/******/ 				var moduleId = queueItem.id;
/******/ 				var chain = queueItem.chain;
/******/ 				module = installedModules[moduleId];
/******/ 				if (
/******/ 					!module ||
/******/ 					(module.hot._selfAccepted && !module.hot._selfInvalidated)
/******/ 				)
/******/ 					continue;
/******/ 				if (module.hot._selfDeclined) {
/******/ 					return {
/******/ 						type: "self-declined",
/******/ 						chain: chain,
/******/ 						moduleId: moduleId
/******/ 					};
/******/ 				}
/******/ 				if (module.hot._main) {
/******/ 					return {
/******/ 						type: "unaccepted",
/******/ 						chain: chain,
/******/ 						moduleId: moduleId
/******/ 					};
/******/ 				}
/******/ 				for (var i = 0; i < module.parents.length; i++) {
/******/ 					var parentId = module.parents[i];
/******/ 					var parent = installedModules[parentId];
/******/ 					if (!parent) continue;
/******/ 					if (parent.hot._declinedDependencies[moduleId]) {
/******/ 						return {
/******/ 							type: "declined",
/******/ 							chain: chain.concat([parentId]),
/******/ 							moduleId: moduleId,
/******/ 							parentId: parentId
/******/ 						};
/******/ 					}
/******/ 					if (outdatedModules.indexOf(parentId) !== -1) continue;
/******/ 					if (parent.hot._acceptedDependencies[moduleId]) {
/******/ 						if (!outdatedDependencies[parentId])
/******/ 							outdatedDependencies[parentId] = [];
/******/ 						addAllToSet(outdatedDependencies[parentId], [moduleId]);
/******/ 						continue;
/******/ 					}
/******/ 					delete outdatedDependencies[parentId];
/******/ 					outdatedModules.push(parentId);
/******/ 					queue.push({
/******/ 						chain: chain.concat([parentId]),
/******/ 						id: parentId
/******/ 					});
/******/ 				}
/******/ 			}
/******/
/******/ 			return {
/******/ 				type: "accepted",
/******/ 				moduleId: updateModuleId,
/******/ 				outdatedModules: outdatedModules,
/******/ 				outdatedDependencies: outdatedDependencies
/******/ 			};
/******/ 		}
/******/
/******/ 		function addAllToSet(a, b) {
/******/ 			for (var i = 0; i < b.length; i++) {
/******/ 				var item = b[i];
/******/ 				if (a.indexOf(item) === -1) a.push(item);
/******/ 			}
/******/ 		}
/******/
/******/ 		// at begin all updates modules are outdated
/******/ 		// the "outdated" status can propagate to parents if they don't accept the children
/******/ 		var outdatedDependencies = {};
/******/ 		var outdatedModules = [];
/******/ 		var appliedUpdate = {};
/******/
/******/ 		var warnUnexpectedRequire = function warnUnexpectedRequire() {
/******/ 			console.warn(
/******/ 				"[HMR] unexpected require(" + result.moduleId + ") to disposed module"
/******/ 			);
/******/ 		};
/******/
/******/ 		for (var id in hotUpdate) {
/******/ 			if (Object.prototype.hasOwnProperty.call(hotUpdate, id)) {
/******/ 				moduleId = toModuleId(id);
/******/ 				/** @type {TODO} */
/******/ 				var result;
/******/ 				if (hotUpdate[id]) {
/******/ 					result = getAffectedStuff(moduleId);
/******/ 				} else {
/******/ 					result = {
/******/ 						type: "disposed",
/******/ 						moduleId: id
/******/ 					};
/******/ 				}
/******/ 				/** @type {Error|false} */
/******/ 				var abortError = false;
/******/ 				var doApply = false;
/******/ 				var doDispose = false;
/******/ 				var chainInfo = "";
/******/ 				if (result.chain) {
/******/ 					chainInfo = "\nUpdate propagation: " + result.chain.join(" -> ");
/******/ 				}
/******/ 				switch (result.type) {
/******/ 					case "self-declined":
/******/ 						if (options.onDeclined) options.onDeclined(result);
/******/ 						if (!options.ignoreDeclined)
/******/ 							abortError = new Error(
/******/ 								"Aborted because of self decline: " +
/******/ 									result.moduleId +
/******/ 									chainInfo
/******/ 							);
/******/ 						break;
/******/ 					case "declined":
/******/ 						if (options.onDeclined) options.onDeclined(result);
/******/ 						if (!options.ignoreDeclined)
/******/ 							abortError = new Error(
/******/ 								"Aborted because of declined dependency: " +
/******/ 									result.moduleId +
/******/ 									" in " +
/******/ 									result.parentId +
/******/ 									chainInfo
/******/ 							);
/******/ 						break;
/******/ 					case "unaccepted":
/******/ 						if (options.onUnaccepted) options.onUnaccepted(result);
/******/ 						if (!options.ignoreUnaccepted)
/******/ 							abortError = new Error(
/******/ 								"Aborted because " + moduleId + " is not accepted" + chainInfo
/******/ 							);
/******/ 						break;
/******/ 					case "accepted":
/******/ 						if (options.onAccepted) options.onAccepted(result);
/******/ 						doApply = true;
/******/ 						break;
/******/ 					case "disposed":
/******/ 						if (options.onDisposed) options.onDisposed(result);
/******/ 						doDispose = true;
/******/ 						break;
/******/ 					default:
/******/ 						throw new Error("Unexception type " + result.type);
/******/ 				}
/******/ 				if (abortError) {
/******/ 					hotSetStatus("abort");
/******/ 					return Promise.reject(abortError);
/******/ 				}
/******/ 				if (doApply) {
/******/ 					appliedUpdate[moduleId] = hotUpdate[moduleId];
/******/ 					addAllToSet(outdatedModules, result.outdatedModules);
/******/ 					for (moduleId in result.outdatedDependencies) {
/******/ 						if (
/******/ 							Object.prototype.hasOwnProperty.call(
/******/ 								result.outdatedDependencies,
/******/ 								moduleId
/******/ 							)
/******/ 						) {
/******/ 							if (!outdatedDependencies[moduleId])
/******/ 								outdatedDependencies[moduleId] = [];
/******/ 							addAllToSet(
/******/ 								outdatedDependencies[moduleId],
/******/ 								result.outdatedDependencies[moduleId]
/******/ 							);
/******/ 						}
/******/ 					}
/******/ 				}
/******/ 				if (doDispose) {
/******/ 					addAllToSet(outdatedModules, [result.moduleId]);
/******/ 					appliedUpdate[moduleId] = warnUnexpectedRequire;
/******/ 				}
/******/ 			}
/******/ 		}
/******/
/******/ 		// Store self accepted outdated modules to require them later by the module system
/******/ 		var outdatedSelfAcceptedModules = [];
/******/ 		for (i = 0; i < outdatedModules.length; i++) {
/******/ 			moduleId = outdatedModules[i];
/******/ 			if (
/******/ 				installedModules[moduleId] &&
/******/ 				installedModules[moduleId].hot._selfAccepted &&
/******/ 				// removed self-accepted modules should not be required
/******/ 				appliedUpdate[moduleId] !== warnUnexpectedRequire &&
/******/ 				// when called invalidate self-accepting is not possible
/******/ 				!installedModules[moduleId].hot._selfInvalidated
/******/ 			) {
/******/ 				outdatedSelfAcceptedModules.push({
/******/ 					module: moduleId,
/******/ 					parents: installedModules[moduleId].parents.slice(),
/******/ 					errorHandler: installedModules[moduleId].hot._selfAccepted
/******/ 				});
/******/ 			}
/******/ 		}
/******/
/******/ 		// Now in "dispose" phase
/******/ 		hotSetStatus("dispose");
/******/ 		Object.keys(hotAvailableFilesMap).forEach(function(chunkId) {
/******/ 			if (hotAvailableFilesMap[chunkId] === false) {
/******/ 				hotDisposeChunk(chunkId);
/******/ 			}
/******/ 		});
/******/
/******/ 		var idx;
/******/ 		var queue = outdatedModules.slice();
/******/ 		while (queue.length > 0) {
/******/ 			moduleId = queue.pop();
/******/ 			module = installedModules[moduleId];
/******/ 			if (!module) continue;
/******/
/******/ 			var data = {};
/******/
/******/ 			// Call dispose handlers
/******/ 			var disposeHandlers = module.hot._disposeHandlers;
/******/ 			for (j = 0; j < disposeHandlers.length; j++) {
/******/ 				cb = disposeHandlers[j];
/******/ 				cb(data);
/******/ 			}
/******/ 			hotCurrentModuleData[moduleId] = data;
/******/
/******/ 			// disable module (this disables requires from this module)
/******/ 			module.hot.active = false;
/******/
/******/ 			// remove module from cache
/******/ 			delete installedModules[moduleId];
/******/
/******/ 			// when disposing there is no need to call dispose handler
/******/ 			delete outdatedDependencies[moduleId];
/******/
/******/ 			// remove "parents" references from all children
/******/ 			for (j = 0; j < module.children.length; j++) {
/******/ 				var child = installedModules[module.children[j]];
/******/ 				if (!child) continue;
/******/ 				idx = child.parents.indexOf(moduleId);
/******/ 				if (idx >= 0) {
/******/ 					child.parents.splice(idx, 1);
/******/ 				}
/******/ 			}
/******/ 		}
/******/
/******/ 		// remove outdated dependency from module children
/******/ 		var dependency;
/******/ 		var moduleOutdatedDependencies;
/******/ 		for (moduleId in outdatedDependencies) {
/******/ 			if (
/******/ 				Object.prototype.hasOwnProperty.call(outdatedDependencies, moduleId)
/******/ 			) {
/******/ 				module = installedModules[moduleId];
/******/ 				if (module) {
/******/ 					moduleOutdatedDependencies = outdatedDependencies[moduleId];
/******/ 					for (j = 0; j < moduleOutdatedDependencies.length; j++) {
/******/ 						dependency = moduleOutdatedDependencies[j];
/******/ 						idx = module.children.indexOf(dependency);
/******/ 						if (idx >= 0) module.children.splice(idx, 1);
/******/ 					}
/******/ 				}
/******/ 			}
/******/ 		}
/******/
/******/ 		// Now in "apply" phase
/******/ 		hotSetStatus("apply");
/******/
/******/ 		if (hotUpdateNewHash !== undefined) {
/******/ 			hotCurrentHash = hotUpdateNewHash;
/******/ 			hotUpdateNewHash = undefined;
/******/ 		}
/******/ 		hotUpdate = undefined;
/******/
/******/ 		// insert new code
/******/ 		for (moduleId in appliedUpdate) {
/******/ 			if (Object.prototype.hasOwnProperty.call(appliedUpdate, moduleId)) {
/******/ 				modules[moduleId] = appliedUpdate[moduleId];
/******/ 			}
/******/ 		}
/******/
/******/ 		// call accept handlers
/******/ 		var error = null;
/******/ 		for (moduleId in outdatedDependencies) {
/******/ 			if (
/******/ 				Object.prototype.hasOwnProperty.call(outdatedDependencies, moduleId)
/******/ 			) {
/******/ 				module = installedModules[moduleId];
/******/ 				if (module) {
/******/ 					moduleOutdatedDependencies = outdatedDependencies[moduleId];
/******/ 					var callbacks = [];
/******/ 					for (i = 0; i < moduleOutdatedDependencies.length; i++) {
/******/ 						dependency = moduleOutdatedDependencies[i];
/******/ 						cb = module.hot._acceptedDependencies[dependency];
/******/ 						if (cb) {
/******/ 							if (callbacks.indexOf(cb) !== -1) continue;
/******/ 							callbacks.push(cb);
/******/ 						}
/******/ 					}
/******/ 					for (i = 0; i < callbacks.length; i++) {
/******/ 						cb = callbacks[i];
/******/ 						try {
/******/ 							cb(moduleOutdatedDependencies);
/******/ 						} catch (err) {
/******/ 							if (options.onErrored) {
/******/ 								options.onErrored({
/******/ 									type: "accept-errored",
/******/ 									moduleId: moduleId,
/******/ 									dependencyId: moduleOutdatedDependencies[i],
/******/ 									error: err
/******/ 								});
/******/ 							}
/******/ 							if (!options.ignoreErrored) {
/******/ 								if (!error) error = err;
/******/ 							}
/******/ 						}
/******/ 					}
/******/ 				}
/******/ 			}
/******/ 		}
/******/
/******/ 		// Load self accepted modules
/******/ 		for (i = 0; i < outdatedSelfAcceptedModules.length; i++) {
/******/ 			var item = outdatedSelfAcceptedModules[i];
/******/ 			moduleId = item.module;
/******/ 			hotCurrentParents = item.parents;
/******/ 			hotCurrentChildModule = moduleId;
/******/ 			try {
/******/ 				__webpack_require__(moduleId);
/******/ 			} catch (err) {
/******/ 				if (typeof item.errorHandler === "function") {
/******/ 					try {
/******/ 						item.errorHandler(err);
/******/ 					} catch (err2) {
/******/ 						if (options.onErrored) {
/******/ 							options.onErrored({
/******/ 								type: "self-accept-error-handler-errored",
/******/ 								moduleId: moduleId,
/******/ 								error: err2,
/******/ 								originalError: err
/******/ 							});
/******/ 						}
/******/ 						if (!options.ignoreErrored) {
/******/ 							if (!error) error = err2;
/******/ 						}
/******/ 						if (!error) error = err;
/******/ 					}
/******/ 				} else {
/******/ 					if (options.onErrored) {
/******/ 						options.onErrored({
/******/ 							type: "self-accept-errored",
/******/ 							moduleId: moduleId,
/******/ 							error: err
/******/ 						});
/******/ 					}
/******/ 					if (!options.ignoreErrored) {
/******/ 						if (!error) error = err;
/******/ 					}
/******/ 				}
/******/ 			}
/******/ 		}
/******/
/******/ 		// handle errors in accept handlers and self accepted module load
/******/ 		if (error) {
/******/ 			hotSetStatus("fail");
/******/ 			return Promise.reject(error);
/******/ 		}
/******/
/******/ 		if (hotQueuedInvalidatedModules) {
/******/ 			return hotApplyInternal(options).then(function(list) {
/******/ 				outdatedModules.forEach(function(moduleId) {
/******/ 					if (list.indexOf(moduleId) < 0) list.push(moduleId);
/******/ 				});
/******/ 				return list;
/******/ 			});
/******/ 		}
/******/
/******/ 		hotSetStatus("idle");
/******/ 		return new Promise(function(resolve) {
/******/ 			resolve(outdatedModules);
/******/ 		});
/******/ 	}
/******/
/******/ 	function hotApplyInvalidatedModules() {
/******/ 		if (hotQueuedInvalidatedModules) {
/******/ 			if (!hotUpdate) hotUpdate = {};
/******/ 			hotQueuedInvalidatedModules.forEach(hotApplyInvalidatedModule);
/******/ 			hotQueuedInvalidatedModules = undefined;
/******/ 			return true;
/******/ 		}
/******/ 	}
/******/
/******/ 	function hotApplyInvalidatedModule(moduleId) {
/******/ 		if (!Object.prototype.hasOwnProperty.call(hotUpdate, moduleId))
/******/ 			hotUpdate[moduleId] = modules[moduleId];
/******/ 	}
/******/
/******/ 	// The module cache
/******/ 	var installedModules = {};
/******/
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/
/******/ 		// Check if module is in cache
/******/ 		if(installedModules[moduleId]) {
/******/ 			return installedModules[moduleId].exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = installedModules[moduleId] = {
/******/ 			i: moduleId,
/******/ 			l: false,
/******/ 			exports: {},
/******/ 			hot: hotCreateModule(moduleId),
/******/ 			parents: (hotCurrentParentsTemp = hotCurrentParents, hotCurrentParents = [], hotCurrentParentsTemp),
/******/ 			children: []
/******/ 		};
/******/
/******/ 		// Execute the module function
/******/ 		modules[moduleId].call(module.exports, module, module.exports, hotCreateRequire(moduleId));
/******/
/******/ 		// Flag the module as loaded
/******/ 		module.l = true;
/******/
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/
/******/
/******/ 	// expose the modules object (__webpack_modules__)
/******/ 	__webpack_require__.m = modules;
/******/
/******/ 	// expose the module cache
/******/ 	__webpack_require__.c = installedModules;
/******/
/******/ 	// define getter function for harmony exports
/******/ 	__webpack_require__.d = function(exports, name, getter) {
/******/ 		if(!__webpack_require__.o(exports, name)) {
/******/ 			Object.defineProperty(exports, name, { enumerable: true, get: getter });
/******/ 		}
/******/ 	};
/******/
/******/ 	// define __esModule on exports
/******/ 	__webpack_require__.r = function(exports) {
/******/ 		if(typeof Symbol !== 'undefined' && Symbol.toStringTag) {
/******/ 			Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 		}
/******/ 		Object.defineProperty(exports, '__esModule', { value: true });
/******/ 	};
/******/
/******/ 	// create a fake namespace object
/******/ 	// mode & 1: value is a module id, require it
/******/ 	// mode & 2: merge all properties of value into the ns
/******/ 	// mode & 4: return value when already ns object
/******/ 	// mode & 8|1: behave like require
/******/ 	__webpack_require__.t = function(value, mode) {
/******/ 		if(mode & 1) value = __webpack_require__(value);
/******/ 		if(mode & 8) return value;
/******/ 		if((mode & 4) && typeof value === 'object' && value && value.__esModule) return value;
/******/ 		var ns = Object.create(null);
/******/ 		__webpack_require__.r(ns);
/******/ 		Object.defineProperty(ns, 'default', { enumerable: true, value: value });
/******/ 		if(mode & 2 && typeof value != 'string') for(var key in value) __webpack_require__.d(ns, key, function(key) { return value[key]; }.bind(null, key));
/******/ 		return ns;
/******/ 	};
/******/
/******/ 	// getDefaultExport function for compatibility with non-harmony modules
/******/ 	__webpack_require__.n = function(module) {
/******/ 		var getter = module && module.__esModule ?
/******/ 			function getDefault() { return module['default']; } :
/******/ 			function getModuleExports() { return module; };
/******/ 		__webpack_require__.d(getter, 'a', getter);
/******/ 		return getter;
/******/ 	};
/******/
/******/ 	// Object.prototype.hasOwnProperty.call
/******/ 	__webpack_require__.o = function(object, property) { return Object.prototype.hasOwnProperty.call(object, property); };
/******/
/******/ 	// __webpack_public_path__
/******/ 	__webpack_require__.p = "";
/******/
/******/ 	// __webpack_hash__
/******/ 	__webpack_require__.h = function() { return hotCurrentHash; };
/******/
/******/
/******/ 	// Load entry module and return exports
/******/ 	return hotCreateRequire("./openassessment/xblock/static/js/src/lms/editors/oa_editor_tinymce.js")(__webpack_require__.s = "./openassessment/xblock/static/js/src/lms/editors/oa_editor_tinymce.js");
/******/ })
/************************************************************************/
/******/ ({

/***/ "./openassessment/xblock/static/js/src/lms/editors/oa_editor_tinymce.js":
/*!******************************************************************************!*\
  !*** ./openassessment/xblock/static/js/src/lms/editors/oa_editor_tinymce.js ***!
  \******************************************************************************/
/*! no static exports found */
/***/ (function(module, exports) {

eval("function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError(\"Cannot call a class as a function\"); } }\n\nfunction _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if (\"value\" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }\n\nfunction _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }\n\nfunction _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }\n\n/**\n Handles Response Editor of tinymce type.\n * */\n(function (define) {\n  var dependencies = []; // Create a flag to determine if we are in lms\n\n  var isLMS = typeof window.LmsRuntime !== 'undefined'; // Determine which css file should be loaded to style text in the editor\n\n  var baseUrl = '/static/studio/js/vendor/tinymce/js/tinymce/';\n\n  if (isLMS) {\n    baseUrl = '/static/js/vendor/tinymce/js/tinymce/';\n  }\n\n  if (typeof window.tinymce === 'undefined') {\n    // If tinymce is not available, we need to load it\n    dependencies.push('tinymce');\n    dependencies.push('jquery.tinymce');\n  }\n\n  define(dependencies, function () {\n    var EditorTinymce = /*#__PURE__*/function () {\n      function EditorTinymce() {\n        _classCallCheck(this, EditorTinymce);\n\n        _defineProperty(this, \"editorInstances\", []);\n      }\n\n      _createClass(EditorTinymce, [{\n        key: \"getTinyMCEConfig\",\n\n        /**\n         Build and return TinyMCE Configuration.\n         * */\n        value: function getTinyMCEConfig(readonly) {\n          var config = {\n            menubar: false,\n            statusbar: false,\n            base_url: baseUrl,\n            theme: 'silver',\n            skin: 'studio-tmce5',\n            content_css: 'studio-tmce5',\n            height: '300',\n            schema: 'html5',\n            plugins: 'code image link lists',\n            toolbar: 'formatselect | bold italic underline | link blockquote image | numlist bullist outdent indent | strikethrough | code | undo redo'\n          }; // if readonly hide toolbar, menubar and statusbar\n\n          if (readonly) {\n            config = Object.assign(config, {\n              toolbar: false,\n              readonly: 1\n            });\n          }\n\n          return config;\n        }\n        /**\n         Loads TinyMCE editor.\n         Args:\n         elements (object): editor elements selected by jQuery\n         * */\n\n      }, {\n        key: \"load\",\n        value: function load(elements) {\n          this.elements = elements;\n          var ctrl = this;\n          return Promise.all(this.elements.map(function () {\n            var _this = this;\n\n            // check if it's readonly\n            var disabled = $(this).attr('disabled'); // In LMS with multiple Unit containing ORA Block with tinyMCE enabled,\n            // We need to destroy if any previously intialized editor exists for current element.\n\n            var id = $(this).attr('id');\n\n            if (id !== undefined) {\n              var existingEditor = tinymce.get(id); // eslint-disable-line\n\n              if (existingEditor) {\n                existingEditor.destroy();\n              }\n            }\n\n            var config = ctrl.getTinyMCEConfig(disabled);\n            return new Promise(function (resolve) {\n              config.setup = function (editor) {\n                return editor.on('init', function () {\n                  ctrl.editorInstances.push(editor);\n                  resolve();\n                });\n              };\n\n              $(_this).tinymce(config);\n            });\n          }));\n        }\n        /**\n         Set on change listener to the editor.\n         Args:\n         handler (Function)\n         * */\n\n      }, {\n        key: \"setOnChangeListener\",\n        value: function setOnChangeListener(handler) {\n          var _this2 = this;\n\n          ['change', 'keyup', 'drop', 'paste'].forEach(function (eventName) {\n            _this2.editorInstances.forEach(function (editor) {\n              editor.on(eventName, handler);\n            });\n          });\n        }\n        /**\n         Set the response texts.\n         Retrieve the response texts.\n         Args:\n         texts (array of strings): If specified, the texts to set for the response.\n         Returns:\n         array of strings: The current response texts.\n         * */\n\n        /* eslint-disable-next-line consistent-return */\n\n      }, {\n        key: \"response\",\n        value: function response(texts) {\n          if (typeof texts === 'undefined') {\n            return this.editorInstances.map(function (editor) {\n              return editor.getContent();\n            });\n          }\n\n          this.editorInstances.forEach(function (editor, index) {\n            editor.setContent(texts[index]);\n          });\n        }\n      }]);\n\n      return EditorTinymce;\n    }(); // return a function, to be able to create new instance every time.\n\n\n    return function () {\n      return new EditorTinymce();\n    };\n  });\n}).call(window, window.define || window.RequireJS.define);//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIndlYnBhY2s6Ly8vLi9vcGVuYXNzZXNzbWVudC94YmxvY2svc3RhdGljL2pzL3NyYy9sbXMvZWRpdG9ycy9vYV9lZGl0b3JfdGlueW1jZS5qcz82MmZhIl0sIm5hbWVzIjpbImRlZmluZSIsImRlcGVuZGVuY2llcyIsImlzTE1TIiwid2luZG93IiwiTG1zUnVudGltZSIsImJhc2VVcmwiLCJ0aW55bWNlIiwicHVzaCIsIkVkaXRvclRpbnltY2UiLCJyZWFkb25seSIsImNvbmZpZyIsIm1lbnViYXIiLCJzdGF0dXNiYXIiLCJiYXNlX3VybCIsInRoZW1lIiwic2tpbiIsImNvbnRlbnRfY3NzIiwiaGVpZ2h0Iiwic2NoZW1hIiwicGx1Z2lucyIsInRvb2xiYXIiLCJPYmplY3QiLCJhc3NpZ24iLCJlbGVtZW50cyIsImN0cmwiLCJQcm9taXNlIiwiYWxsIiwibWFwIiwiZGlzYWJsZWQiLCIkIiwiYXR0ciIsImlkIiwidW5kZWZpbmVkIiwiZXhpc3RpbmdFZGl0b3IiLCJnZXQiLCJkZXN0cm95IiwiZ2V0VGlueU1DRUNvbmZpZyIsInJlc29sdmUiLCJzZXR1cCIsImVkaXRvciIsIm9uIiwiZWRpdG9ySW5zdGFuY2VzIiwiaGFuZGxlciIsImZvckVhY2giLCJldmVudE5hbWUiLCJ0ZXh0cyIsImdldENvbnRlbnQiLCJpbmRleCIsInNldENvbnRlbnQiLCJjYWxsIiwiUmVxdWlyZUpTIl0sIm1hcHBpbmdzIjoiOzs7Ozs7OztBQUFBOzs7QUFJQSxDQUFDLFVBQVVBLE1BQVYsRUFBa0I7QUFDakIsTUFBTUMsWUFBWSxHQUFHLEVBQXJCLENBRGlCLENBR2pCOztBQUNBLE1BQU1DLEtBQUssR0FBRyxPQUFPQyxNQUFNLENBQUNDLFVBQWQsS0FBNkIsV0FBM0MsQ0FKaUIsQ0FNakI7O0FBQ0EsTUFBSUMsT0FBTyxHQUFHLDhDQUFkOztBQUNBLE1BQUlILEtBQUosRUFBVztBQUNURyxXQUFPLEdBQUcsdUNBQVY7QUFDRDs7QUFFRCxNQUFJLE9BQU9GLE1BQU0sQ0FBQ0cs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QUpEO0FBS0Q7QUFFRDs7Ozs7Ozs7O0FBUUE7O0FBeEZ1QjtBQUFBO0FBQUEsaUNBeUZkRyxLQXpGYyxFQXlGUDtBQUNkLGNBQUksT0FBT0EsS0FBUCxLQUFpQixXQUFyQixFQUFrQztBQUNoQyxtQkFBTyxLQUFLSixlQUFMLENBQXFCZCxHQUFyQixDQUF5QixVQUFBWSxNQUFNO0FBQUEscUJBQUlBLE1BQU0sQ0FBQ08sVUFBUCxFQUFKO0FBQUEsYUFBL0IsQ0FBUDtBQUNEOztBQUNELGVBQUtMLGVBQUwsQ0FBcUJFLE9BQXJCLENBQTZCLFVBQUNKLE1BQUQsRUFBU1EsS0FBVCxFQUFtQjtBQUM5Q1Isa0JBQU0sQ0FBQ1MsVUFBUCxDQUFrQkgsS0FBSyxDQUFDRSxLQUFELENBQXZCO0FBQ0QsV0FGRDtBQUdEO0FBaEdzQjs7QUFBQTtBQUFBLFNBbUd6Qjs7O0FBQ0EsV0FBTyxZQUFZO0FBQ2pCLGFBQU8sSUFBSXZDLGFBQUosRUFBUDtBQUNELEtBRkQ7QUFHRCxHQXZHSyxDQUFOO0FBd0dELENBMUhELEVBMEhHeUMsSUExSEgsQ0EwSFE5QyxNQTFIUixFQTBIZ0JBLE1BQU0sQ0FBQ0gsTUFBUCxJQUFpQkcsTUFBTSxDQUFDK0MsU0FBUCxDQUFpQmxELE1BMUhsRCIsImZpbGUiOiIuL29wZW5hc3Nlc3NtZW50L3hibG9jay9zdGF0aWMvanMvc3JjL2xtcy9lZGl0b3JzL29hX2VkaXRvcl90aW55bWNlLmpzLmpzIiwic291cmNlc0NvbnRlbnQiOlsiLyoqXG4gSGFuZGxlcyBSZXNwb25zZSBFZGl0b3Igb2YgdGlueW1jZSB0eXBlLlxuICogKi9cblxuKGZ1bmN0aW9uIChkZWZpbmUpIHtcbiAgY29uc3QgZGVwZW5kZW5jaWVzID0gW107XG5cbiAgLy8gQ3JlYXRlIGEgZmxhZyB0byBkZXRlcm1pbmUgaWYgd2UgYXJlIGluIGxtc1xuICBjb25zdCBpc0xNUyA9IHR5cGVvZiB3aW5kb3cuTG1zUnVudGltZSAhPT0gJ3VuZGVmaW5lZCc7XG5cbiAgLy8gRGV0ZXJtaW5lIHdoaWNoIGNzcyBmaWxlIHNob3VsZCBiZSBsb2FkZWQgdG8gc3R5bGUgdGV4dCBpbiB0aGUgZWRpdG9yXG4gIGxldCBiYXNlVXJsID0gJy9zdGF0aWMvc3R1ZGlvL2pzL3ZlbmRvci90aW55bWNlL2pzL3RpbnltY2UvJztcbiAgaWYgKGlzTE1TKSB7XG4gICAgYmFzZVVybCA9ICcvc3RhdGljL2pzL3ZlbmRvci90aW55bWNlL2pzL3RpbnltY2UvJztcbiAgfVxuXG4gIGlmICh0eXBlb2Ygd2luZG93LnRpbnltY2UgPT09ICd1bmRlZmluZWQnKSB7XG4gICAgLy8gSWYgdGlueW1jZSBpcyBub3QgYXZhaWxhYmxlLCB3ZSBuZWVkIHRvIGxvYWQgaXRcbiAgICBkZXBlbmRlbmNpZXMucHVzaCgndGlueW1jZScpO1xuICAgIGRlcGVuZGVuY2llcy5wdXNoKCdqcXVlcnkudGlueW1jZScpO1xuICB9XG5cbiAgZGVmaW5lKGRlcGVuZGVuY2llcywgKCkgPT4ge1xuICAgIGNsYXNzIEVkaXRvclRpbnltY2Uge1xuICAgICAgZWRpdG9ySW5zdGFuY2VzID0gW107XG5cbiAgICAgIC8qKlxuICAgICAgIEJ1aWxkIGFuZCByZXR1cm4gVGlueU1DRSBDb25maWd1cmF0aW9uLlxuICAgICAgICogKi9cbiAgICAgIGdldFRpbnlNQ0VDb25maWcocmVhZG9ubHkpIHtcbiAgICAgICAgbGV0IGNvbmZpZyA9IHtcbiAgICAgICAgICBtZW51YmFyOiBmYWxzZSxcbiAgICAgICAgICBzdGF0dXNiYXI6IGZhbHNlLFxuICAgICAgICAgIGJhc2VfdXJsOiBiYXNlVXJsLFxuICAgICAgICAgIHRoZW1lOiAnc2lsdmVyJyxcbiAgICAgICAgICBza2luOiAnc3R1ZGlvLXRtY2U1JyxcbiAgICAgICAgICBjb250ZW50X2NzczogJ3N0dWRpby10bWNlNScsXG4gICAgICAgICAgaGVpZ2h0OiAnMzAwJyxcbiAgICAgICAgICBzY2hlbWE6ICdodG1sNScsXG4gICAgICAgICAgcGx1Z2luczogJ2NvZGUgaW1hZ2UgbGluayBsaXN0cycsXG4gICAgICAgICAgdG9vbGJhcjogJ2Zvcm1hdHNlbGVjdCB8IGJvbGQgaXRhbGljIHVuZGVybGluZSB8IGxpbmsgYmxvY2txdW90ZSBpbWFnZSB8IG51bWxpc3QgYnVsbGlzdCBvdXRkZW50IGluZGVudCB8IHN0cmlrZXRocm91Z2ggfCBjb2RlIHwgdW5kbyByZWRvJyxcbiAgICAgICAgfTtcblxuICAgICAgICAvLyBpZiByZWFkb25seSBoaWRlIHRvb2xiYXIsIG1lbnViYXIgYW5kIHN0YXR1c2JhclxuICAgICAgICBpZiAocmVhZG9ubHkpIHtcbiAgICAgICAgICBjb25maWcgPSBPYmplY3QuYXNzaWduKGNvbmZpZywge1xuICAgICAgICAgICAgdG9vbGJhcjogZmFsc2UsXG4gICAgICAgICAgICByZWFkb25seTogMSxcbiAgICAgICAgICB9KTtcbiAgICAgICAgfVxuXG4gICAgICAgIHJldHVybiBjb25maWc7XG4gICAgICB9XG5cbiAgICAgIC8qKlxuICAgICAgIExvYWRzIFRpbnlNQ0UgZWRpdG9yLlxuICAgICAgIEFyZ3M6XG4gICAgICAgZWxlbWVudHMgKG9iamVjdCk6IGVkaXRvciBlbGVtZW50cyBzZWxlY3RlZCBieSBqUXVlcnlcbiAgICAgICAqICovXG4gICAgICBsb2FkKGVsZW1lbnRzKSB7XG4gICAgICAgIHRoaXMuZWxlbWVudHMgPSBlbGVtZW50cztcblxuICAgICAgICBjb25zdCBjdHJsID0gdGhpcztcblxuICAgICAgICByZXR1cm4gUHJvbWlzZS5hbGwodGhpcy5lbGVtZW50cy5tYXAoZnVuY3Rpb24gKCkge1xuICAgICAgICAgIC8vIGNoZWNrIGlmIGl0J3MgcmVhZG9ubHlcbiAgICAgICAgICBjb25zdCBkaXNhYmxlZCA9ICQodGhpcykuYXR0cignZGlzYWJsZWQnKTtcblxuICAgICAgICAgIC8vIEluIExNUyB3aXRoIG11bHRpcGxlIFVuaXQgY29udGFpbmluZyBPUkEgQmxvY2sgd2l0aCB0aW55TUNFIGVuYWJsZWQsXG4gICAgICAgICAgLy8gV2UgbmVlZCB0byBkZXN0cm95IGlmIGFueSBwcmV2aW91c2x5IGludGlhbGl6ZWQgZWRpdG9yIGV4aXN0cyBmb3IgY3VycmVudCBlbGVtZW50LlxuICAgICAgICAgIGNvbnN0IGlkID0gJCh0aGlzKS5hdHRyKCdpZCcpO1xuICAgICAgICAgIGlmIChpZCAhPT0gdW5kZWZpbmVkKSB7XG4gICAgICAgICAgICBjb25zdCBleGlzdGluZ0VkaXRvciA9IHRpbnltY2UuZ2V0KGlkKTsgLy8gZXNsaW50LWRpc2FibGUtbGluZVxuICAgICAgICAgICAgaWYgKGV4aXN0aW5nRWRpdG9yKSB7XG4gICAgICAgICAgICAgIGV4aXN0aW5nRWRpdG9yLmRlc3Ryb3koKTtcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9XG5cbiAgICAgICAgICBjb25zdCBjb25maWcgPSBjdHJsLmdldFRpbnlNQ0VDb25maWcoZGlzYWJsZWQpO1xuICAgICAgICAgIHJldHVybiBuZXcgUHJvbWlzZShyZXNvbHZlID0+IHtcbiAgICAgICAgICAgIGNvbmZpZy5zZXR1cCA9IGVkaXRvciA9PiBlZGl0b3Iub24oJ2luaXQnLCAoKSA9PiB7XG4gICAgICAgICAgICAgIGN0cmwuZWRpdG9ySW5zdGFuY2VzLnB1c2goZWRpdG9yKTtcbiAgICAgICAgICAgICAgcmVzb2x2ZSgpO1xuICAgICAgICAgICAgfSk7XG4gICAgICAgICAgICAkKHRoaXMpLnRpbnltY2UoY29uZmlnKTtcbiAgICAgICAgICB9KTtcbiAgICAgICAgfSkpO1xuICAgICAgfVxuXG4gICAgICAvKipcbiAgICAgICBTZXQgb24gY2hhbmdlIGxpc3RlbmVyIHRvIHRoZSBlZGl0b3IuXG4gICAgICAgQXJnczpcbiAgICAgICBoYW5kbGVyIChGdW5jdGlvbilcbiAgICAgICAqICovXG4gICAgICBzZXRPbkNoYW5nZUxpc3RlbmVyKGhhbmRsZXIpIHtcbiAgICAgICAgWydjaGFuZ2UnLCAna2V5dXAnLCAnZHJvcCcsICdwYXN0ZSddLmZvckVhY2goZXZlbnROYW1lID0+IHtcbiAgICAgICAgICB0aGlzLmVkaXRvckluc3RhbmNlcy5mb3JFYWNoKGVkaXRvciA9PiB7XG4gICAgICAgICAgICBlZGl0b3Iub24oZXZlbnROYW1lLCBoYW5kbGVyKTtcbiAgICAgICAgICB9KTtcbiAgICAgICAgfSk7XG4gICAgICB9XG5cbiAgICAgIC8qKlxuICAgICAgIFNldCB0aGUgcmVzcG9uc2UgdGV4dHMuXG4gICAgICAgUmV0cmlldmUgdGhlIHJlc3BvbnNlIHRleHRzLlxuICAgICAgIEFyZ3M6XG4gICAgICAgdGV4dHMgKGFycmF5IG9mIHN0cmluZ3MpOiBJZiBzcGVjaWZpZWQsIHRoZSB0ZXh0cyB0byBzZXQgZm9yIHRoZSByZXNwb25zZS5cbiAgICAgICBSZXR1cm5zOlxuICAgICAgIGFycmF5IG9mIHN0cmluZ3M6IFRoZSBjdXJyZW50IHJlc3BvbnNlIHRleHRzLlxuICAgICAgICogKi9cbiAgICAgIC8qIGVzbGludC1kaXNhYmxlLW5leHQtbGluZSBjb25zaXN0ZW50LXJldHVybiAqL1xuICAgICAgcmVzcG9uc2UodGV4dHMpIHtcbiAgICAgICAgaWYgKHR5cGVvZiB0ZXh0cyA9PT0gJ3VuZGVmaW5lZCcpIHtcbiAgICAgICAgICByZXR1cm4gdGhpcy5lZGl0b3JJbnN0YW5jZXMubWFwKGVkaXRvciA9PiBlZGl0b3IuZ2V0Q29udGVudCgpKTtcbiAgICAgICAgfVxuICAgICAgICB0aGlzLmVkaXRvckluc3RhbmNlcy5mb3JFYWNoKChlZGl0b3IsIGluZGV4KSA9PiB7XG4gICAgICAgICAgZWRpdG9yLnNldENvbnRlbnQodGV4dHNbaW5kZXhdKTtcbiAgICAgICAgfSk7XG4gICAgICB9XG4gICAgfVxuXG4gICAgLy8gcmV0dXJuIGEgZnVuY3Rpb24sIHRvIGJlIGFibGUgdG8gY3JlYXRlIG5ldyBpbnN0YW5jZSBldmVyeSB0aW1lLlxuICAgIHJldHVybiBmdW5jdGlvbiAoKSB7XG4gICAgICByZXR1cm4gbmV3IEVkaXRvclRpbnltY2UoKTtcbiAgICB9O1xuICB9KTtcbn0pLmNhbGwod2luZG93LCB3aW5kb3cuZGVmaW5lIHx8IHdpbmRvdy5SZXF1aXJlSlMuZGVmaW5lKTtcbiJdLCJzb3VyY2VSb290IjoiIn0=\n//# sourceURL=webpack-internal:///./openassessment/xblock/static/js/src/lms/editors/oa_editor_tinymce.js\n");

/***/ })

/******/ });