package handlers

import (
	"net/http"
	"github.com/gin-gonic/gin"
)

type SearchRequest struct {
	Query        string `json:"query" binding:"required,min=3"`
	Jurisdiction string `json:"jurisdiction"`
	Depth        int    `json:"depth"`
	Limit        int    `json:"limit"`
}

type SearchResult struct {
	DocumentID   string  `json:"document_id"`
	Title        string  `json:"title"`
	Jurisdiction string  `json:"jurisdiction"`
	Score        float64 `json:"score"`
	Snippet      string  `json:"snippet"`
}

func Search(c *gin.Context) {
	var req SearchRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if req.Limit == 0 {
		req.Limit = 10
	}
	if req.Depth == 0 {
		req.Depth = 2
	}
	// Delegate to Python search service via gRPC
	results, err := searchService.HybridSearch(c.Request.Context(), req.Query, req.Jurisdiction, req.Limit, req.Depth)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "search failed"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"results": results, "count": len(results)})
}
