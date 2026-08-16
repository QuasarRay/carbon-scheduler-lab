#pragma once
#ifndef GILRAII_H
#define GILRAII_H

#define PY_SSIZE_T_CLEAN
#include "stdafx.h"

class GILRAII
{
private:
	PyGILState_STATE m_gilState;

public:
	GILRAII();
    ~GILRAII();

    GILRAII( GILRAII &other ) = delete;
	GILRAII( GILRAII &&other ) = delete;
};

#endif // GILRAII_H
