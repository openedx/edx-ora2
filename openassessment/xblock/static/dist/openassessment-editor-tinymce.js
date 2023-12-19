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
/******/ 	var hotCurrentHash = "b2a9cf4156c3630c8859";
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

eval("function _typeof(o) { \"@babel/helpers - typeof\"; return _typeof = \"function\" == typeof Symbol && \"symbol\" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && \"function\" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? \"symbol\" : typeof o; }, _typeof(o); }\nfunction _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError(\"Cannot call a class as a function\"); } }\nfunction _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if (\"value\" in descriptor) descriptor.writable = true; Object.defineProperty(target, _toPropertyKey(descriptor.key), descriptor); } }\nfunction _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); Object.defineProperty(Constructor, \"prototype\", { writable: false }); return Constructor; }\nfunction _defineProperty(obj, key, value) { key = _toPropertyKey(key); if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }\nfunction _toPropertyKey(arg) { var key = _toPrimitive(arg, \"string\"); return _typeof(key) === \"symbol\" ? key : String(key); }\nfunction _toPrimitive(input, hint) { if (_typeof(input) !== \"object\" || input === null) return input; var prim = input[Symbol.toPrimitive]; if (prim !== undefined) { var res = prim.call(input, hint || \"default\"); if (_typeof(res) !== \"object\") return res; throw new TypeError(\"@@toPrimitive must return a primitive value.\"); } return (hint === \"string\" ? String : Number)(input); }\n/**\n Handles Response Editor of tinymce type.\n * */\n\n(function (define) {\n  var dependencies = [];\n\n  // Create a flag to determine if we are in lms\n  var isLMS = typeof window.LmsRuntime !== 'undefined';\n\n  // Determine which css file should be loaded to style text in the editor\n  var baseUrl = '/static/studio/js/vendor/tinymce/js/tinymce/';\n  if (isLMS) {\n    baseUrl = '/static/js/vendor/tinymce/js/tinymce/';\n  }\n  if (typeof window.tinymce === 'undefined') {\n    // If tinymce is not available, we need to load it\n    dependencies.push('tinymce');\n    dependencies.push('jquery.tinymce');\n  }\n  define(dependencies, function () {\n    var EditorTinymce = /*#__PURE__*/function () {\n      function EditorTinymce() {\n        _classCallCheck(this, EditorTinymce);\n        _defineProperty(this, \"editorInstances\", []);\n      }\n      _createClass(EditorTinymce, [{\n        key: \"getTinyMCEConfig\",\n        value:\n        /**\n         Build and return TinyMCE Configuration.\n         * */\n        function getTinyMCEConfig(readonly) {\n          var config = {\n            menubar: false,\n            statusbar: false,\n            base_url: baseUrl,\n            theme: 'silver',\n            skin: 'studio-tmce5',\n            content_css: 'studio-tmce5',\n            height: '300',\n            schema: 'html5',\n            plugins: 'code image link lists',\n            toolbar: 'formatselect | bold italic underline | link blockquote image | numlist bullist outdent indent | strikethrough | code | undo redo'\n          };\n\n          // if readonly hide toolbar, menubar and statusbar\n          if (readonly) {\n            config = Object.assign(config, {\n              toolbar: false,\n              readonly: 1\n            });\n          }\n          return config;\n        }\n\n        /**\n         Loads TinyMCE editor.\n         Args:\n         elements (object): editor elements selected by jQuery\n         * */\n      }, {\n        key: \"load\",\n        value: function load(elements) {\n          this.elements = elements;\n          var ctrl = this;\n          return Promise.all(this.elements.map(function () {\n            var _this = this;\n            // check if it's readonly\n            var disabled = $(this).attr('disabled');\n\n            // In LMS with multiple Unit containing ORA Block with tinyMCE enabled,\n            // We need to destroy if any previously intialized editor exists for current element.\n            var id = $(this).attr('id');\n            if (id !== undefined) {\n              var existingEditor = tinymce.get(id); // eslint-disable-line\n              if (existingEditor) {\n                existingEditor.destroy();\n              }\n            }\n            var config = ctrl.getTinyMCEConfig(disabled);\n            return new Promise(function (resolve) {\n              config.setup = function (editor) {\n                return editor.on('init', function () {\n                  ctrl.editorInstances.push(editor);\n                  resolve();\n                });\n              };\n              $(_this).tinymce(config);\n            });\n          }));\n        }\n\n        /**\n         Set on change listener to the editor.\n         Args:\n         handler (Function)\n         * */\n      }, {\n        key: \"setOnChangeListener\",\n        value: function setOnChangeListener(handler) {\n          var _this2 = this;\n          ['change', 'keyup', 'drop', 'paste'].forEach(function (eventName) {\n            _this2.editorInstances.forEach(function (editor) {\n              editor.on(eventName, handler);\n            });\n          });\n        }\n\n        /**\n         Set the response texts.\n         Retrieve the response texts.\n         Args:\n         texts (array of strings): If specified, the texts to set for the response.\n         Returns:\n         array of strings: The current response texts.\n         * */\n        /* eslint-disable-next-line consistent-return */\n      }, {\n        key: \"response\",\n        value: function response(texts) {\n          if (typeof texts === 'undefined') {\n            return this.editorInstances.map(function (editor) {\n              return editor.getContent();\n            });\n          }\n          this.editorInstances.forEach(function (editor, index) {\n            editor.setContent(texts[index]);\n          });\n        }\n      }]);\n      return EditorTinymce;\n    }(); // return a function, to be able to create new instance every time.\n    return function () {\n      return new EditorTinymce();\n    };\n  });\n}).call(window, window.define || window.RequireJS.define);//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIndlYnBhY2s6Ly8vLi9vcGVuYXNzZXNzbWVudC94YmxvY2svc3RhdGljL2pzL3NyYy9sbXMvZWRpdG9ycy9vYV9lZGl0b3JfdGlueW1jZS5qcz82MmZhIl0sIm5hbWVzIjpbImRlZmluZSIsImRlcGVuZGVuY2llcyIsImlzTE1TIiwid2luZG93IiwiTG1zUnVudGltZSIsImJhc2VVcmwiLCJ0aW55bWNlIiwicHVzaCIsIkVkaXRvclRpbnltY2UiLCJfY2xhc3NDYWxsQ2hlY2siLCJfZGVmaW5lUHJvcGVydHkiLCJfY3JlYXRlQ2xhc3MiLCJrZXkiLCJ2YWx1ZSIsImdldFRpbnlNQ0VDb25maWciLCJyZWFkb25seSIsImNvbmZpZyIsIm1lbnViYXIiLCJzdGF0dXNiYXIiLCJiYXNlX3VybCIsInRoZW1lIiwic2tpbiIsImNvbnRlbnRfY3NzIiwiaGVpZ2h0Iiwic2NoZW1hIiwicGx1Z2lucyIsInRvb2xiYXIiLCJPYmplY3QiLCJhc3NpZ24iLCJsb2FkIiwiZWxlbWVudHMiLCJjdHJsIiwiUHJvbWlzZSIsImFsbCIsIm1hcCIsIl90aGlzIiwiZGlzYWJsZWQiLCIkIiwiYXR0ciIsImlkIiwidW5kZWZpbmVkIiwiZXhpc3RpbmdFZGl0b3IiLCJnZXQiLCJkZXN0cm95IiwicmVzb2x2ZSIsInNldHVwIiwiZWRpdG9yIiwib24iLCJlZGl0b3JJbnN0YW5jZXMiLCJzZXRPbkNoYW5nZUxpc3RlbmVyIiwiaGFuZGxlciIsIl90aGlzMiIsImZvckVhY2giLCJldmVudE5hbWUiLCJyZXNwb25zZSIsInRleHRzIiwiZ2V0Q29udGVudCIsImluZGV4Iiwic2V0Q29udGVudCIsImNhbGwiLCJSZXF1aXJlSlMiXSwibWFwcGluZ3MiOiI7Ozs7Ozs7QUFBQTtBQUNBO0FBQ0E7O0FBRUEsQ0FBQyxVQUFVQSxNQUFNLEVBQUU7RUFDakIsSUFBTUMsWUFBWSxHQUFHLEVBQUU7O0VBRXZCO0VBQ0EsSUFBTUMsS0FBSyxHQUFHLE9BQU9DLE1BQU0sQ0FBQ0MsVUFBVSxLQUFLLFdB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Y2svc3RhdGljL2pzL3NyYy9sbXMvZWRpdG9ycy9vYV9lZGl0b3JfdGlueW1jZS5qcy5qcyIsInNvdXJjZXNDb250ZW50IjpbIi8qKlxuIEhhbmRsZXMgUmVzcG9uc2UgRWRpdG9yIG9mIHRpbnltY2UgdHlwZS5cbiAqICovXG5cbihmdW5jdGlvbiAoZGVmaW5lKSB7XG4gIGNvbnN0IGRlcGVuZGVuY2llcyA9IFtdO1xuXG4gIC8vIENyZWF0ZSBhIGZsYWcgdG8gZGV0ZXJtaW5lIGlmIHdlIGFyZSBpbiBsbXNcbiAgY29uc3QgaXNMTVMgPSB0eXBlb2Ygd2luZG93Lkxtc1J1bnRpbWUgIT09ICd1bmRlZmluZWQnO1xuXG4gIC8vIERldGVybWluZSB3aGljaCBjc3MgZmlsZSBzaG91bGQgYmUgbG9hZGVkIHRvIHN0eWxlIHRleHQgaW4gdGhlIGVkaXRvclxuICBsZXQgYmFzZVVybCA9ICcvc3RhdGljL3N0dWRpby9qcy92ZW5kb3IvdGlueW1jZS9qcy90aW55bWNlLyc7XG4gIGlmIChpc0xNUykge1xuICAgIGJhc2VVcmwgPSAnL3N0YXRpYy9qcy92ZW5kb3IvdGlueW1jZS9qcy90aW55bWNlLyc7XG4gIH1cblxuICBpZiAodHlwZW9mIHdpbmRvdy50aW55bWNlID09PSAndW5kZWZpbmVkJykge1xuICAgIC8vIElmIHRpbnltY2UgaXMgbm90IGF2YWlsYWJsZSwgd2UgbmVlZCB0byBsb2FkIGl0XG4gICAgZGVwZW5kZW5jaWVzLnB1c2goJ3RpbnltY2UnKTtcbiAgICBkZXBlbmRlbmNpZXMucHVzaCgnanF1ZXJ5LnRpbnltY2UnKTtcbiAgfVxuXG4gIGRlZmluZShkZXBlbmRlbmNpZXMsICgpID0+IHtcbiAgICBjbGFzcyBFZGl0b3JUaW55bWNlIHtcbiAgICAgIGVkaXRvckluc3RhbmNlcyA9IFtdO1xuXG4gICAgICAvKipcbiAgICAgICBCdWlsZCBhbmQgcmV0dXJuIFRpbnlNQ0UgQ29uZmlndXJhdGlvbi5cbiAgICAgICAqICovXG4gICAgICBnZXRUaW55TUNFQ29uZmlnKHJlYWRvbmx5KSB7XG4gICAgICAgIGxldCBjb25maWcgPSB7XG4gICAgICAgICAgbWVudWJhcjogZmFsc2UsXG4gICAgICAgICAgc3RhdHVzYmFyOiBmYWxzZSxcbiAgICAgICAgICBiYXNlX3VybDogYmFzZVVybCxcbiAgICAgICAgICB0aGVtZTogJ3NpbHZlcicsXG4gICAgICAgICAgc2tpbjogJ3N0dWRpby10bWNlNScsXG4gICAgICAgICAgY29udGVudF9jc3M6ICdzdHVkaW8tdG1jZTUnLFxuICAgICAgICAgIGhlaWdodDogJzMwMCcsXG4gICAgICAgICAgc2NoZW1hOiAnaHRtbDUnLFxuICAgICAgICAgIHBsdWdpbnM6ICdjb2RlIGltYWdlIGxpbmsgbGlzdHMnLFxuICAgICAgICAgIHRvb2xiYXI6ICdmb3JtYXRzZWxlY3QgfCBib2xkIGl0YWxpYyB1bmRlcmxpbmUgfCBsaW5rIGJsb2NrcXVvdGUgaW1hZ2UgfCBudW1saXN0IGJ1bGxpc3Qgb3V0ZGVudCBpbmRlbnQgfCBzdHJpa2V0aHJvdWdoIHwgY29kZSB8IHVuZG8gcmVkbycsXG4gICAgICAgIH07XG5cbiAgICAgICAgLy8gaWYgcmVhZG9ubHkgaGlkZSB0b29sYmFyLCBtZW51YmFyIGFuZCBzdGF0dXNiYXJcbiAgICAgICAgaWYgKHJlYWRvbmx5KSB7XG4gICAgICAgICAgY29uZmlnID0gT2JqZWN0LmFzc2lnbihjb25maWcsIHtcbiAgICAgICAgICAgIHRvb2xiYXI6IGZhbHNlLFxuICAgICAgICAgICAgcmVhZG9ubHk6IDEsXG4gICAgICAgICAgfSk7XG4gICAgICAgIH1cblxuICAgICAgICByZXR1cm4gY29uZmlnO1xuICAgICAgfVxuXG4gICAgICAvKipcbiAgICAgICBMb2FkcyBUaW55TUNFIGVkaXRvci5cbiAgICAgICBBcmdzOlxuICAgICAgIGVsZW1lbnRzIChvYmplY3QpOiBlZGl0b3IgZWxlbWVudHMgc2VsZWN0ZWQgYnkgalF1ZXJ5XG4gICAgICAgKiAqL1xuICAgICAgbG9hZChlbGVtZW50cykge1xuICAgICAgICB0aGlzLmVsZW1lbnRzID0gZWxlbWVudHM7XG5cbiAgICAgICAgY29uc3QgY3RybCA9IHRoaXM7XG5cbiAgICAgICAgcmV0dXJuIFByb21pc2UuYWxsKHRoaXMuZWxlbWVudHMubWFwKGZ1bmN0aW9uICgpIHtcbiAgICAgICAgICAvLyBjaGVjayBpZiBpdCdzIHJlYWRvbmx5XG4gICAgICAgICAgY29uc3QgZGlzYWJsZWQgPSAkKHRoaXMpLmF0dHIoJ2Rpc2FibGVkJyk7XG5cbiAgICAgICAgICAvLyBJbiBMTVMgd2l0aCBtdWx0aXBsZSBVbml0IGNvbnRhaW5pbmcgT1JBIEJsb2NrIHdpdGggdGlueU1DRSBlbmFibGVkLFxuICAgICAgICAgIC8vIFdlIG5lZWQgdG8gZGVzdHJveSBpZiBhbnkgcHJldmlvdXNseSBpbnRpYWxpemVkIGVkaXRvciBleGlzdHMgZm9yIGN1cnJlbnQgZWxlbWVudC5cbiAgICAgICAgICBjb25zdCBpZCA9ICQodGhpcykuYXR0cignaWQnKTtcbiAgICAgICAgICBpZiAoaWQgIT09IHVuZGVmaW5lZCkge1xuICAgICAgICAgICAgY29uc3QgZXhpc3RpbmdFZGl0b3IgPSB0aW55bWNlLmdldChpZCk7IC8vIGVzbGludC1kaXNhYmxlLWxpbmVcbiAgICAgICAgICAgIGlmIChleGlzdGluZ0VkaXRvcikge1xuICAgICAgICAgICAgICBleGlzdGluZ0VkaXRvci5kZXN0cm95KCk7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfVxuXG4gICAgICAgICAgY29uc3QgY29uZmlnID0gY3RybC5nZXRUaW55TUNFQ29uZmlnKGRpc2FibGVkKTtcbiAgICAgICAgICByZXR1cm4gbmV3IFByb21pc2UocmVzb2x2ZSA9PiB7XG4gICAgICAgICAgICBjb25maWcuc2V0dXAgPSBlZGl0b3IgPT4gZWRpdG9yLm9uKCdpbml0JywgKCkgPT4ge1xuICAgICAgICAgICAgICBjdHJsLmVkaXRvckluc3RhbmNlcy5wdXNoKGVkaXRvcik7XG4gICAgICAgICAgICAgIHJlc29sdmUoKTtcbiAgICAgICAgICAgIH0pO1xuICAgICAgICAgICAgJCh0aGlzKS50aW55bWNlKGNvbmZpZyk7XG4gICAgICAgICAgfSk7XG4gICAgICAgIH0pKTtcbiAgICAgIH1cblxuICAgICAgLyoqXG4gICAgICAgU2V0IG9uIGNoYW5nZSBsaXN0ZW5lciB0byB0aGUgZWRpdG9yLlxuICAgICAgIEFyZ3M6XG4gICAgICAgaGFuZGxlciAoRnVuY3Rpb24pXG4gICAgICAgKiAqL1xuICAgICAgc2V0T25DaGFuZ2VMaXN0ZW5lcihoYW5kbGVyKSB7XG4gICAgICAgIFsnY2hhbmdlJywgJ2tleXVwJywgJ2Ryb3AnLCAncGFzdGUnXS5mb3JFYWNoKGV2ZW50TmFtZSA9PiB7XG4gICAgICAgICAgdGhpcy5lZGl0b3JJbnN0YW5jZXMuZm9yRWFjaChlZGl0b3IgPT4ge1xuICAgICAgICAgICAgZWRpdG9yLm9uKGV2ZW50TmFtZSwgaGFuZGxlcik7XG4gICAgICAgICAgfSk7XG4gICAgICAgIH0pO1xuICAgICAgfVxuXG4gICAgICAvKipcbiAgICAgICBTZXQgdGhlIHJlc3BvbnNlIHRleHRzLlxuICAgICAgIFJldHJpZXZlIHRoZSByZXNwb25zZSB0ZXh0cy5cbiAgICAgICBBcmdzOlxuICAgICAgIHRleHRzIChhcnJheSBvZiBzdHJpbmdzKTogSWYgc3BlY2lmaWVkLCB0aGUgdGV4dHMgdG8gc2V0IGZvciB0aGUgcmVzcG9uc2UuXG4gICAgICAgUmV0dXJuczpcbiAgICAgICBhcnJheSBvZiBzdHJpbmdzOiBUaGUgY3VycmVudCByZXNwb25zZSB0ZXh0cy5cbiAgICAgICAqICovXG4gICAgICAvKiBlc2xpbnQtZGlzYWJsZS1uZXh0LWxpbmUgY29uc2lzdGVudC1yZXR1cm4gKi9cbiAgICAgIHJlc3BvbnNlKHRleHRzKSB7XG4gICAgICAgIGlmICh0eXBlb2YgdGV4dHMgPT09ICd1bmRlZmluZWQnKSB7XG4gICAgICAgICAgcmV0dXJuIHRoaXMuZWRpdG9ySW5zdGFuY2VzLm1hcChlZGl0b3IgPT4gZWRpdG9yLmdldENvbnRlbnQoKSk7XG4gICAgICAgIH1cbiAgICAgICAgdGhpcy5lZGl0b3JJbnN0YW5jZXMuZm9yRWFjaCgoZWRpdG9yLCBpbmRleCkgPT4ge1xuICAgICAgICAgIGVkaXRvci5zZXRDb250ZW50KHRleHRzW2luZGV4XSk7XG4gICAgICAgIH0pO1xuICAgICAgfVxuICAgIH1cblxuICAgIC8vIHJldHVybiBhIGZ1bmN0aW9uLCB0byBiZSBhYmxlIHRvIGNyZWF0ZSBuZXcgaW5zdGFuY2UgZXZlcnkgdGltZS5cbiAgICByZXR1cm4gZnVuY3Rpb24gKCkge1xuICAgICAgcmV0dXJuIG5ldyBFZGl0b3JUaW55bWNlKCk7XG4gICAgfTtcbiAgfSk7XG59KS5jYWxsKHdpbmRvdywgd2luZG93LmRlZmluZSB8fCB3aW5kb3cuUmVxdWlyZUpTLmRlZmluZSk7XG4iXSwic291cmNlUm9vdCI6IiJ9\n//# sourceURL=webpack-internal:///./openassessment/xblock/static/js/src/lms/editors/oa_editor_tinymce.js\n");

/***/ })

/******/ });