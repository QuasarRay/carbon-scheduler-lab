#include "GILRAII.h"

GILRAII::GILRAII()
{
	m_gilState = PyGILState_Ensure();
}

GILRAII::~GILRAII()
{
	PyGILState_Release( m_gilState );
}
